class AddRouteTableException(Exception):
    pass


class RouteTableOperations(object):
    def __init__(self, logger, aws_ec2_datamodel, ec2_session, ec2_client, reservation, vpc_service,
                 route_table_service, subnet_service, network_interface_service):
        """
        :param cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel aws_ec2_datamodel:
        :param cloudshell.cp.aws.domain.services.ec2.vpc.VPCService vpc_service: VPC Service
        :param cloudshell.cp.aws.domain.services.ec2.route_table.RouteTablesService route_table_service:
        :param cloudshell.cp.aws.domain.services.ec2.subnet.SubnetService subnet_service:
        :param cloudshell.cp.aws.domain.services.ec2.network_interface.NetworkInterfaceService network_interface_service:
        """
        self.ec2_session = ec2_session
        self.ec2_client = ec2_client
        self.aws_ec2_datamodel = aws_ec2_datamodel
        self.reservation = reservation
        self.logger = logger
        self.vpc_service = vpc_service
        self.route_table_service = route_table_service
        self.subnet_service = subnet_service
        self.network_interface_service = network_interface_service

        self._vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=self.ec2_session,
                                                              reservation_id=self.reservation.reservation_id)
        self._peering_connection = self._get_peering_connection()

    def _get_peering_connection(self):
        result = self.vpc_service.get_peering_connection_by_reservation_id(self.ec2_session,
                                                                           self.reservation.reservation_id)
        return result[0] if result else None

    def _add_peering_connection_route(self, route_table):
        if self._peering_connection:
            self.route_table_service.add_route_to_peered_vpc(route_table, self._peering_connection.id,
                                                             self._peering_connection.requester_vpc.cidr_block)

    def _assign_subnets(self, route_table_id, subnets):
        for subnet_id in subnets:
            self.subnet_service.unset_subnet_route_table(self.ec2_client, subnet_id)
            self.subnet_service.set_subnet_route_table(self.ec2_client, subnet_id, route_table_id)

    def _add_route_interface(self, route_table, int_ip_addr, target_cidr):
        interface = self.network_interface_service.find_network_interface(self._vpc, int_ip_addr)
        if interface:
            self.route_table_service.add_route_to_interface(route_table, interface.id, target_cidr)
        else:
            raise AddRouteTableException('Cannot find Network Interface with private IP {}'.format(int_ip_addr))

    def _add_route_internet_gateway(self, route_table):
        result = self.vpc_service.get_all_internet_gateways(self._vpc)
        gateway = result[0] if result else None
        if gateway:
            self.route_table_service.add_route_to_internet_gateway(route_table, gateway.id)
        else:
            raise AddRouteTableException('Cannot find Internet Gateway')

    def _add_route_nat_gateway(self, route_table, subnet_id, nat_gw_int_ip, target_cidr):
        nat_gateway_id = self.subnet_service.get_nat_gateway_id_with_int_ip(self.ec2_client, subnet_id, nat_gw_int_ip)
        if nat_gateway_id:
            self.route_table_service.add_route_to_nat_gateway(route_table, nat_gateway_id, target_cidr)
        else:
            raise AddRouteTableException("Cannot find Nat Gateway with IP {} for subnet {}".format(nat_gw_int_ip, subnet_id))

    def _add_route(self, route_table, route_model, subnets):
        """
        :param ec2.RouteTable route_table:
        :param cloudshell.cp.aws.models.network_actions_models.RouteResourceModel route_model:
        :param [ec2.Subnet] subnets:
        :return:
        """
        if route_model.next_hop_type == route_model.NEXT_HOPE_TYPE.INTERFACE:
            self._add_route_interface(route_table, route_model.next_hop_address, route_model.address_prefix)
        elif route_model.next_hop_type == route_model.NEXT_HOPE_TYPE.INTERNET_GATEWAY:
            self._add_route_internet_gateway(route_table)
        elif route_model.next_hop_type == route_model.NEXT_HOPE_TYPE.NAT_GATEWAY:
            self._add_route_nat_gateway(route_table, subnets[0], route_model.next_hop_address,
                                        route_model.address_prefix)
        else:
            raise AddRouteTableException('Cannot determine requested next_hope_type')

    def operate_create_table_request(self, route_table_request_model):
        """
        Handle add route table request
        :param cloudshell.cp.aws.models.network_actions_models.RouteTableRequestResourceModel route_table_request_model:
        :return:
        """
        table_name = "{} Reservation: ".format(route_table_request_model.name, self.reservation.reservation_id)
        table_name = route_table_request_model.name
        route_table = self.route_table_service.create_route_table(self.ec2_session, self.reservation, self._vpc.id,
                                                                  table_name)

        self._assign_subnets(route_table.id, route_table_request_model.subnets)
        self._add_peering_connection_route(route_table)

        for route_model in route_table_request_model.routes:
            self._add_route(route_table, route_model, route_table_request_model.subnets)

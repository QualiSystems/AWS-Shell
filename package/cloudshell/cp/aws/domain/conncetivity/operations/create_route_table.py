from cloudshell.cp.aws.domain.common.exceptions import AddRouteTableException


class CreateRouteTableOperation(object):
    """
    Handle request for creating route table and adding routes
    """

    def __init__(self, vpc_service, route_table_service, subnet_service, network_interface_service):
        """
        :param cloudshell.cp.aws.domain.services.ec2.vpc.VPCService vpc_service: VPC Service
        :param cloudshell.cp.aws.domain.services.ec2.route_table.RouteTablesService route_table_service:
        :param cloudshell.cp.aws.domain.services.ec2.subnet.SubnetService subnet_service:
        :param cloudshell.cp.aws.domain.services.ec2.network_interface.NetworkInterfaceService network_interface_service:
        """
        self._vpc_service = vpc_service
        self._route_table_service = route_table_service
        self._subnet_service = subnet_service
        self._network_interface_service = network_interface_service

    def _get_peering_connection(self, ec2_session, reservation):
        result = self._vpc_service.get_peering_connection_by_reservation_id(ec2_session, reservation.reservation_id)
        return result[0] if result else None

    def _add_peering_connection_route(self, route_table, ec2_session, reservation):
        peering_connection = self._get_peering_connection(ec2_session, reservation)
        if peering_connection:
            self._route_table_service.add_route_to_peered_vpc(route_table, peering_connection.id,
                                                              peering_connection.requester_vpc.cidr_block)

    def _assign_subnets(self, route_table_id, subnets, ec2_client):
        subnets_backup = {}
        try:
            for subnet_id in subnets:
                subnets_backup[subnet_id] = self._subnet_service.unset_subnet_route_table(ec2_client, subnet_id)
                self._subnet_service.set_subnet_route_table(ec2_client, subnet_id, route_table_id)
        except:
            for subnet_id, table_id in subnets_backup.items():
                if table_id:
                    self._subnet_service.unset_subnet_route_table(ec2_client, subnet_id)
                    self._subnet_service.set_subnet_route_table(ec2_client, subnet_id, table_id)
            raise

    def _add_route_interface(self, route_table, vpc, int_ip_addr, target_cidr):
        interface = self._network_interface_service.find_network_interface(vpc, int_ip_addr)
        if interface:
            self._route_table_service.add_route_to_interface(route_table, interface.id, target_cidr)
        else:
            raise AddRouteTableException('Cannot find Network Interface with private IP {}'.format(int_ip_addr))

    def _add_route_internet_gateway(self, route_table, vpc):
        result = self._vpc_service.get_all_internet_gateways(vpc)
        gateway = result[0] if result else None
        if gateway:
            self._route_table_service.add_route_to_internet_gateway(route_table, gateway.id)
        else:
            raise AddRouteTableException('Cannot find Internet Gateway')

    def _add_route_nat_gateway(self, route_table, subnet_id, nat_gw_int_ip, target_cidr, ec2_client):
        nat_gateway_id = self._subnet_service.get_nat_gateway_id_with_int_ip(ec2_client, subnet_id, nat_gw_int_ip)
        if nat_gateway_id:
            self._route_table_service.add_route_to_nat_gateway(route_table, nat_gateway_id, target_cidr)
        else:
            raise AddRouteTableException(
                "Cannot find Nat Gateway with IP {} for subnet {}".format(nat_gw_int_ip, subnet_id))

    def _add_route(self, route_table, vpc, route_model, subnets, ec2_client, logger):
        """
        :param ec2.RouteTable route_table:
        :param ec2.Vpc vpc:
        :param cloudshell.cp.aws.models.network_actions_models.RouteResourceModel route_model:
        :param [ec2.Subnet] subnets:
        :param logging.Logger logger:
        :return:
        """
        logger.debug("Create route {}".format(str(route_model)))
        if route_model.next_hop_type == route_model.NEXT_HOPE_TYPE.INTERFACE:
            self._add_route_interface(route_table, vpc, route_model.next_hop_address, route_model.address_prefix)
        elif route_model.next_hop_type == route_model.NEXT_HOPE_TYPE.INTERNET_GATEWAY:
            self._add_route_internet_gateway(route_table, vpc)
        elif route_model.next_hop_type == route_model.NEXT_HOPE_TYPE.NAT_GATEWAY:
            self._add_route_nat_gateway(route_table, subnets[0], route_model.next_hop_address,
                                        route_model.address_prefix, ec2_client)
        else:
            raise AddRouteTableException(
                'Cannot determine requested next_hope_type {}'.format(route_model.next_hop_type))

    def _create_table(self, ec2_session, ec2_client, reservation, route_table_request_model, logger):
        """
        Handle add route table request
        :param boto3.resource ec2_session:
        :param boto3.client ec2_client:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param cloudshell.cp.aws.models.network_actions_models.RouteTableRequestResourceModel route_table_request_model:
        :param logging.Logger logger:
        :return:
        """
        # table_name = "{} Reservation: ".format(route_table_request_model.name, self.reservation.reservation_id)
        logger.info("Create route table {}".format(str(route_table_request_model)))
        vpc = self._vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                         reservation_id=reservation.reservation_id)
        table_name = route_table_request_model.name
        route_table = self._route_table_service.create_route_table(ec2_session, reservation, vpc.id,
                                                                   table_name)

        try:
            for route_model in route_table_request_model.routes:
                self._add_route(route_table, vpc, route_model, route_table_request_model.subnets, ec2_client, logger)

            self._add_peering_connection_route(route_table, ec2_session, reservation)
            self._assign_subnets(route_table.id, route_table_request_model.subnets, ec2_client)
        except:
            logger.error("Create route table unsuccessful, removing route table")
            self._route_table_service.delete_table(route_table)
            raise

    def operate_create_tables_request(self, ec2_session, ec2_client, reservation, route_table_request_models, logger):
        """
        Handle add route table request
        :param boto3.resource ec2_session:
        :param boto3.client ec2_client:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param list[cloudshell.cp.aws.models.network_actions_models.RouteTableRequestResourceModel] route_table_request_models:
        :param logging.Logger logger:
        :return:
        """
        exceptions = []
        for route_table_request in route_table_request_models:
            try:
                self._create_table(ec2_session, ec2_client, reservation, route_table_request, logger)
            except Exception as e:
                logger.exception("Error occurred:")
                exceptions.append(e)

        if exceptions:
            raise Exception('CreateRouteTables finished with errors, see logs for more details.')

from mock import Mock, patch, call
from unittest2 import TestCase

from cloudshell.cp.aws.domain.common.exceptions import AddRouteTableException
from cloudshell.cp.aws.domain.conncetivity.operations.create_route_table import CreateRouteTableOperation


class TestCreateRouteTableOperation(TestCase):

    def setUp(self):
        self._vpc_service = Mock()
        self._route_table_service = Mock()
        self._subnet_service = Mock()
        self._network_interface_service = Mock()
        self._create_route_table_operation = CreateRouteTableOperation(self._vpc_service, self._route_table_service,
                                                                       self._subnet_service,
                                                                       self._network_interface_service)

    def test_get_peering_connection(self):
        result = Mock()
        self._vpc_service.get_peering_connection_by_reservation_id.return_value = [result]
        ec2_session = Mock()
        reservation = Mock()
        reservation_id = Mock()
        reservation.reservation_id = reservation_id
        self.assertEquals(self._create_route_table_operation._get_peering_connection(ec2_session, reservation),
                          result)
        self._vpc_service.get_peering_connection_by_reservation_id.assert_called_once_with(ec2_session, reservation_id)

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._get_peering_connection")
    def test_add_peering_connection_route(self, get_peering_connection):
        route_table = Mock()
        ec2_session = Mock()
        reservation = Mock()
        peering_connection = Mock()
        get_peering_connection.return_value = peering_connection
        peering_connection_id = Mock()
        peering_connection_cidr_block = Mock()
        peering_connection.id = peering_connection_id
        peering_connection.requester_vpc.cidr_block = peering_connection_cidr_block
        self._create_route_table_operation._add_peering_connection_route(route_table, ec2_session, reservation)
        get_peering_connection.assert_called_once_with(ec2_session, reservation)
        self._route_table_service.add_route_to_peered_vpc.assert_called_once_with(route_table, peering_connection_id,
                                                                                  peering_connection_cidr_block)

    def test_assign_subnets_no_exception(self):
        route_table_id = Mock()
        subnet_id1 = Mock()
        subnet_id2 = Mock()
        subnets = [subnet_id1, subnet_id2]
        ec2_client = Mock()
        self._create_route_table_operation._assign_subnets(route_table_id, subnets, ec2_client)
        self._subnet_service.unset_subnet_route_table.assert_has_calls(
            [call(ec2_client, subnet_id1), call(ec2_client, subnet_id2)])
        self._subnet_service.set_subnet_route_table.assert_has_calls(
            [call(ec2_client, subnet_id1, route_table_id), call(ec2_client, subnet_id2, route_table_id)])

    def test_assign_subnets_exception(self):
        route_table_id = Mock()
        subnet_id1 = Mock()
        subnet_id2 = Mock()
        backup_id1 = Mock()
        backup_id2 = Mock()
        self._subnet_service.unset_subnet_route_table.side_effect = [backup_id1, backup_id2, route_table_id,
                                                                     route_table_id]
        subnets = [subnet_id1, subnet_id2]
        ec2_client = Mock()
        exception_text = 'Test Exception'
        self._subnet_service.set_subnet_route_table.side_effect = [None, Exception(exception_text), None, None]
        with self.assertRaisesRegex(Exception, exception_text):
            self._create_route_table_operation._assign_subnets(route_table_id, subnets, ec2_client)

        self._subnet_service.unset_subnet_route_table.assert_has_calls(
            [call(ec2_client, subnet_id1), call(ec2_client, subnet_id2), call(ec2_client, subnet_id1),
             call(ec2_client, subnet_id2)])
        self._subnet_service.set_subnet_route_table.assert_has_calls(
            [call(ec2_client, subnet_id1, route_table_id), call(ec2_client, subnet_id2, route_table_id),
             call(ec2_client, subnet_id1, backup_id1), call(ec2_client, subnet_id2, backup_id2)])

    def test_add_route_interface_no_exception(self):
        route_table = Mock()
        vpc = Mock()
        int_ip_addr = Mock()
        target_cidr = Mock()
        interface_id = Mock()
        interface = Mock()
        interface.id = interface_id
        self._network_interface_service.find_network_interface.return_value = interface
        self._create_route_table_operation._add_route_interface(route_table, vpc, int_ip_addr, target_cidr)
        self._network_interface_service.find_network_interface.assert_called_once_with(vpc, int_ip_addr)
        self._route_table_service.add_route_to_interface.assert_called_once_with(route_table, interface_id, target_cidr)

    def test_add_route_interface_exception(self):
        route_table = Mock()
        vpc = Mock()
        int_ip_addr = Mock()
        target_cidr = Mock()
        interface = None
        self._network_interface_service.find_network_interface.return_value = interface
        with self.assertRaisesRegex(AddRouteTableException, "Cannot find Network Interface with private IP"):
            self._create_route_table_operation._add_route_interface(route_table, vpc, int_ip_addr, target_cidr)
        self._network_interface_service.find_network_interface.assert_called_once_with(vpc, int_ip_addr)
        self._route_table_service.add_route_to_interface.assert_not_called()

    def test_add_route_internet_gateway_no_exception(self):
        route_table = Mock()
        vpc = Mock()
        gateway = Mock()
        gateway_id = Mock()
        gateway.id = gateway_id
        self._vpc_service.get_all_internet_gateways.return_value = [gateway]
        self._create_route_table_operation._add_route_internet_gateway(route_table, vpc)
        self._vpc_service.get_all_internet_gateways.assert_called_once_with(vpc)
        self._route_table_service.add_route_to_internet_gateway.assert_called_once_with(route_table, gateway_id)

    def test_add_route_internet_gateway_exception(self):
        route_table = Mock()
        vpc = Mock()
        gateway = None
        self._vpc_service.get_all_internet_gateways.return_value = [gateway]
        with self.assertRaisesRegex(AddRouteTableException, 'Cannot find Internet Gateway'):
            self._create_route_table_operation._add_route_internet_gateway(route_table, vpc)
        self._vpc_service.get_all_internet_gateways.assert_called_once_with(vpc)
        self._route_table_service.add_route_to_internet_gateway.assert_not_called()

    def test_add_route_nat_gateway_no_exception(self):
        route_table = Mock()
        subnet_id1 = Mock()
        subnet_id2 = Mock()
        subnets = [subnet_id1, subnet_id2]
        nat_gw_int_ip = Mock()
        target_cidr = Mock()
        ec2_client = Mock()
        nat_gateway_id = Mock()
        self._subnet_service.get_nat_gateway_id_with_int_ip.side_effect = [None, nat_gateway_id]
        self._create_route_table_operation._add_route_nat_gateway(route_table, subnets, nat_gw_int_ip, target_cidr,
                                                                  ec2_client)
        self._subnet_service.get_nat_gateway_id_with_int_ip.assert_has_calls(
            [call(ec2_client, subnet_id1, nat_gw_int_ip), call(ec2_client, subnet_id2, nat_gw_int_ip)])
        self._route_table_service.add_route_to_nat_gateway.assert_called_once_with(route_table, nat_gateway_id,
                                                                                   target_cidr)

    def test_add_route_nat_gateway_exception(self):
        route_table = Mock()
        subnet_id1 = 'subnet-1'
        subnet_id2 = 'subnet-1'
        subnets = subnet_id1, subnet_id2
        nat_gw_int_ip = '10.0.1.1'
        target_cidr = Mock()
        ec2_client = Mock()
        nat_gateway_id = None
        self._subnet_service.get_nat_gateway_id_with_int_ip.side_effect = [None, nat_gateway_id]
        with self.assertRaisesRegex(AddRouteTableException,
                                    "Cannot find Nat Gateway with IP {}".format(nat_gw_int_ip)):
            self._create_route_table_operation._add_route_nat_gateway(route_table, subnets, nat_gw_int_ip,
                                                                      target_cidr,
                                                                      ec2_client)
        self._subnet_service.get_nat_gateway_id_with_int_ip.assert_has_calls(
            [call(ec2_client, subnet_id1, nat_gw_int_ip), call(ec2_client, subnet_id2, nat_gw_int_ip)])
        self._route_table_service.add_route_to_nat_gateway.assert_not_called()

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_interface")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_internet_gateway")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_nat_gateway")
    def test_add_route_for_interface(self, add_route_nat_gateway, add_route_internet_gateway, add_route_interface):
        route_table = Mock()
        vpc = Mock()
        route_model = Mock()
        subnets = Mock()
        ec2_client = Mock()
        logger = Mock()
        hop_type = Mock()
        next_hop_address = Mock()
        address_prefix = Mock()
        route_model.next_hop_type = hop_type
        route_model.next_hop_address = next_hop_address
        route_model.address_prefix = address_prefix
        route_model.NEXT_HOPE_TYPE.INTERFACE = hop_type
        self._create_route_table_operation._add_route(route_table, vpc, route_model, subnets, ec2_client, logger)
        add_route_interface.assert_called_once_with(route_table, vpc, next_hop_address, address_prefix)
        add_route_nat_gateway.assert_not_called()
        add_route_internet_gateway.assert_not_called()

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_interface")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_internet_gateway")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_nat_gateway")
    def test_add_route_for_internet_gateway(self, add_route_nat_gateway, add_route_internet_gateway,
                                            add_route_interface):
        route_table = Mock()
        vpc = Mock()
        route_model = Mock()
        subnets = Mock()
        ec2_client = Mock()
        logger = Mock()
        hop_type = Mock()
        next_hop_address = Mock()
        address_prefix = Mock()
        route_model.next_hop_type = hop_type
        route_model.next_hop_address = next_hop_address
        route_model.address_prefix = address_prefix
        route_model.NEXT_HOPE_TYPE.INTERNET_GATEWAY = hop_type
        self._create_route_table_operation._add_route(route_table, vpc, route_model, subnets, ec2_client, logger)
        add_route_interface.assert_not_called()
        add_route_nat_gateway.assert_not_called()
        add_route_internet_gateway.assert_called_once_with(route_table, vpc)

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_interface")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_internet_gateway")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_nat_gateway")
    def test_add_route_for_nat_gateway(self, add_route_nat_gateway, add_route_internet_gateway,
                                       add_route_interface):
        route_table = Mock()
        vpc = Mock()
        route_model = Mock()
        subnets = [Mock()]
        ec2_client = Mock()
        logger = Mock()
        hop_type = Mock()
        next_hop_address = Mock()
        address_prefix = Mock()
        route_model.next_hop_type = hop_type
        route_model.next_hop_address = next_hop_address
        route_model.address_prefix = address_prefix
        route_model.NEXT_HOPE_TYPE.NAT_GATEWAY = hop_type
        self._create_route_table_operation._add_route(route_table, vpc, route_model, subnets, ec2_client, logger)
        add_route_interface.assert_not_called()
        add_route_nat_gateway.assert_called_once_with(route_table, subnets, route_model.next_hop_address,
                                                      route_model.address_prefix, ec2_client)
        add_route_internet_gateway.assert_not_called()

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_interface")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_internet_gateway")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route_nat_gateway")
    def test_add_route_exception(self, add_route_nat_gateway, add_route_internet_gateway,
                                 add_route_interface):
        route_table = Mock()
        vpc = Mock()
        route_model = Mock()
        subnets = [Mock()]
        ec2_client = Mock()
        logger = Mock()
        hop_type = 'hope_type'
        next_hop_address = Mock()
        address_prefix = Mock()
        route_model.next_hop_type = hop_type
        route_model.next_hop_address = next_hop_address
        route_model.address_prefix = address_prefix
        with self.assertRaisesRegex(AddRouteTableException,
                                    'Cannot determine requested next_hope_type {}'.format(hop_type)):
            self._create_route_table_operation._add_route(route_table, vpc, route_model, subnets, ec2_client, logger)
        add_route_interface.assert_not_called()
        add_route_nat_gateway.assert_not_called()
        add_route_internet_gateway.assert_not_called()

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_peering_connection_route")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._assign_subnets")
    def test_create_table(self, assign_subnets, add_peering_connection_route, add_route):
        ec2_session = Mock()
        ec2_client = Mock()
        reservation_id = Mock()
        reservation = Mock(reservation_id=reservation_id)
        logger = Mock()
        vpc_id = Mock()
        vpc = Mock(id=vpc_id)
        self._vpc_service.find_vpc_for_reservation.return_value = vpc
        route_table_request_model = Mock()
        table_name = Mock()
        route1 = Mock()
        route2 = Mock()
        subnets = Mock()
        route_table_request_model.name = table_name
        route_table_request_model.routes = [route1, route2]
        route_table_request_model.subnets = subnets
        route_table = Mock()
        self._route_table_service.create_route_table.return_value = route_table
        self._create_route_table_operation._create_table(ec2_session, ec2_client, reservation,
                                                         route_table_request_model, logger)
        self._vpc_service.find_vpc_for_reservation.assert_called_once_with(ec2_session=ec2_session,
                                                                           reservation_id=reservation_id)
        self._route_table_service.create_route_table.assert_called_once_with(ec2_session, reservation, vpc_id,
                                                                             table_name)
        add_route.assert_has_calls(
            [call(route_table, vpc, route1, subnets, ec2_client, logger),
             call(route_table, vpc, route2, subnets, ec2_client, logger)])
        add_peering_connection_route.assert_called_once_with(route_table, ec2_session, reservation)
        assign_subnets.assert_called_once_with(route_table.id, route_table_request_model.subnets, ec2_client)

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_route")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._add_peering_connection_route")
    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._assign_subnets")
    def test_create_table_with_exception(self, assign_subnets, add_peering_connection_route, add_route):
        ec2_session = Mock()
        ec2_client = Mock()
        reservation = Mock()
        reservation_id = Mock()
        reservation.reservation_id = reservation_id
        route_table_request_model = Mock()
        logger = Mock()
        vpc = Mock()
        self._vpc_service.find_vpc_for_reservation.return_value = vpc
        table_name = Mock()
        route_table_request_model.name = table_name
        route1 = Mock()
        route2 = Mock()
        route_table_request_model.routes = [route1, route2]
        subnets = Mock()
        route_table_request_model.subnets = subnets
        route_table = Mock()
        self._route_table_service.create_route_table.return_value = route_table
        exception_text = 'Test Exception'
        assign_subnets.side_effect = Exception(exception_text)
        with self.assertRaisesRegex(Exception, exception_text):
            self._create_route_table_operation._create_table(ec2_session, ec2_client, reservation,
                                                             route_table_request_model, logger)
        self._vpc_service.find_vpc_for_reservation.assert_called_once_with(ec2_session=ec2_session,
                                                                           reservation_id=reservation_id)
        self._route_table_service.create_route_table.assert_called_once_with(ec2_session, reservation, vpc.id,
                                                                             table_name)
        add_route.assert_has_calls(
            [call(route_table, vpc, route1, route_table_request_model.subnets, ec2_client, logger),
             call(route_table, vpc, route2, route_table_request_model.subnets, ec2_client, logger)])
        add_peering_connection_route.assert_called_once_with(route_table, ec2_session, reservation)
        assign_subnets.assert_called_once_with(route_table.id, route_table_request_model.subnets, ec2_client)
        self._route_table_service.delete_table.assert_called_once_with(route_table)

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._create_table")
    def test_operate_create_tables_request(self, create_table):
        ec2_session = Mock()
        ec2_client = Mock()
        reservation = Mock()
        request1 = Mock()
        request2 = Mock()
        route_table_request_models = [request1, request2]
        logger = Mock()

        self._create_route_table_operation.operate_create_tables_request(ec2_session, ec2_client, reservation,
                                                                         route_table_request_models, logger)

        create_table.assert_has_calls([call(ec2_session, ec2_client, reservation, request1, logger),
                                       call(ec2_session, ec2_client, reservation, request2, logger)])

    @patch(
        "cloudshell.cp.aws.domain.conncetivity.operations.create_route_table.CreateRouteTableOperation._create_table")
    def test_operate_create_tables_request_exception(self, create_table):
        ec2_session = Mock()
        ec2_client = Mock()
        reservation = Mock()
        request1 = Mock()
        request2 = Mock()
        route_table_request_models = [request1, request2]
        logger = Mock()
        create_table.side_effect = [None, Exception()]
        with self.assertRaisesRegex(Exception, 'CreateRouteTables finished with errors, see logs for more details.'):
            self._create_route_table_operation.operate_create_tables_request(ec2_session, ec2_client, reservation,
                                                                             route_table_request_models, logger)

        create_table.assert_has_calls([call(ec2_session, ec2_client, reservation, request1, logger),
                                       call(ec2_session, ec2_client, reservation, request2, logger)])

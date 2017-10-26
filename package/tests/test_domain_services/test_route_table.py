from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.route_table import RouteTablesService


class TestRouteTableService(TestCase):
    def setUp(self):
        self.ec2_session = Mock()
        self.reservation = Mock()

        self.vpc_id = 'vpc-id'
        self.vpc = Mock()
        self.vpc.route_tables = Mock()
        self.vpc.id = self.vpc_id
        self.ec2_session.Vpc = Mock(return_value=self.vpc)
        self.tag_service = Mock()

        self.mocked_route_table = Mock()
        self.mocked_route_table.associations_attribute = [{}]

        self.route_table_service = RouteTablesService(self.tag_service)

    def test_get_main_route_table(self):
        # prepare
        main_route_table = Mock()
        main_route_table.associations_attribute = [{'Main': True}]
        route_tables = [self.mocked_route_table, main_route_table]
        self.vpc.route_tables.all = Mock(return_value=route_tables)

        # act
        main_rt = self.route_table_service.get_main_route_table(self.ec2_session, self.vpc_id)

        # assert
        self.assertIsNotNone(main_rt)

    def test_get_main_route_table_when_main_route_table_not_available(self):
        # prepare
        route_tables = [self.mocked_route_table]
        self.vpc.route_tables.all = Mock(return_value=route_tables)

        # act
        main_rt = self.route_table_service.get_main_route_table(self.ec2_session, self.vpc_id)

        # assert
        self.assertIsNone(main_rt)

    def test_add_route_to_peered_vpc(self):
        # prepare
        route_table = Mock()
        target_peering_id = 'target_peering_id'
        target_vpc_cidr = 'target_vpc_cidr'

        # act
        self.route_table_service.add_route_to_peered_vpc(route_table=route_table, target_peering_id=target_peering_id,
                                                         target_vpc_cidr=target_vpc_cidr)

        # assert
        route_table.create_route.assert_called_with(DestinationCidrBlock=target_vpc_cidr,
                                                    VpcPeeringConnectionId=target_peering_id)

    def test_add_route_to_internet_gateway(self):
        # prepare
        route_table = Mock()
        target_internet_gateway_id = 'target_internet_gateway_id'

        # act
        self.route_table_service.add_route_to_internet_gateway(route_table=route_table,
                                                               target_internet_gateway_id=target_internet_gateway_id)

        # assert
        route_table.create_route.assert_called_with(GatewayId=target_internet_gateway_id,
                                                    DestinationCidrBlock='0.0.0.0/0')

    def test_delete_blackhole_routes(self):
        # prepare
        active_route = Mock()
        active_route.state = 'active'
        blackhole_route = Mock()
        blackhole_route.state = 'blackhole'

        route_table = Mock()
        route_table.routes = [active_route, blackhole_route]

        # act
        self.route_table_service.delete_blackhole_routes(route_table=route_table)

        # assert
        self.assertTrue(blackhole_route.delete.called)
        self.assertFalse(active_route.delete.called)

    def test_find_first_route_simple_filter_matched(self):
        # prepare
        target_vpc_cidr = '10.0.0.0/24'
        route = Mock()
        route.destination_cidr_block = target_vpc_cidr

        route_table = Mock()
        route_table.routes = [route]

        # act
        result = self.route_table_service.find_first_route(route_table=route_table,
                                                           filters={'destination_cidr_block': target_vpc_cidr})

        # assert
        self.assertEquals(result, route)

    def test_find_first_route_no_filter_matched(self):
        # prepare
        route = Mock()
        route_table = Mock()
        route_table.routes = [route]

        # act
        result = self.route_table_service.find_first_route(route_table=route_table,
                                                           filters={'destination_cidr_block': '10.0.0.0/24'})

        # assert
        self.assertIsNone(result)

    def test_get_custom_route_tables(self):
        # Arrange
        tables = [Mock(), Mock(), Mock()]
        self.route_table_service.get_main_route_table = Mock(return_value=tables[0])
        self.route_table_service.get_all_route_tables = Mock(return_value=tables)
        tables[0].id = "0"
        tables[1].id = "1"
        tables[2].id = "2"
        # Act
        results = self.route_table_service.get_custom_route_tables(ec2_session=self.ec2_session, vpc_id=self.vpc_id)
        # Assert
        self.assertEqual(results, [tables[1], tables[2]])

    def test_create_route_table(self):
        # Arrange
        table = Mock()
        tags = Mock()
        self.vpc.create_route_table = Mock(return_value=table)
        self.tag_service.get_default_tags = Mock(return_value=tags)
        # Act
        self.route_table_service.create_route_table(ec2_session=self.ec2_session, reservation=self.reservation,
                                                    vpc_id=self.vpc_id, table_name="MyTable")
        # Assert
        self.vpc.create_route_table.assert_called_once()
        self.tag_service.get_default_tags.assert_called_once_with("MyTable", self.reservation)
        self.tag_service.set_ec2_resource_tags.assert_called_once_with(table, tags)

    def test_get_route_table(self):
        # Arrange
        table = Mock()
        table.tags = [{"Key":"Name", "Value":"Table1"}]
        self.route_table_service.get_all_route_tables = Mock(return_value=[table])
        # Act
        table1 = self.route_table_service.get_route_table(ec2_session=self.ec2_session, vpc_id=self.vpc_id, table_name="Table1")
        table2 = self.route_table_service.get_route_table(ec2_session=self.ec2_session, vpc_id=self.vpc_id, table_name="Table2")
        # Assert
        self.assertEqual(table1, table)
        self.assertEqual(table2, None)

    def test_delete_table(self):
        # Arrange
        table = Mock()
        # Act
        result = self.route_table_service.delete_table(table)
        # Assert
        table.delete.assert_called_once()
        self.assertTrue(result)
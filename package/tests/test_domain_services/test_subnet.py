from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService


class TestSubnetService(TestCase):
    def setUp(self):
        self.vpc = Mock()
        self.cidr = '10.0.0.0/24'
        self.availability_zone = "a1"
        self.vpc_name = 'name'
        self.reservation_id = 'res'
        self.tag_srv = Mock()
        self.subnet_waiter = Mock()
        self.subnet_srv = SubnetService(self.tag_srv, self.subnet_waiter)

    def test_create_subnet_for_vpc(self):
        subnet = Mock()
        self.vpc.create_subnet = Mock(return_value=subnet)
        self.subnet_srv._get_subnet_name = Mock(return_value=self.vpc_name)

        self.subnet_srv.create_subnet_for_vpc(self.vpc, self.cidr, self.vpc_name, self.availability_zone,
                                              self.reservation_id)

        self.vpc.create_subnet.assert_called_with(CidrBlock=self.cidr, AvailabilityZone='a1')
        self.subnet_waiter.wait.assert_called_with(subnet, self.subnet_waiter.AVAILABLE)
        self.tag_srv.get_default_tags.assert_called_with(self.vpc_name, self.reservation_id)
        self.assertEqual(subnet, self.vpc.create_subnet())

    def test_delete_subnet(self):
        subnet = Mock()
        res = self.subnet_srv.delete_subnet(subnet)
        self.assertTrue(res)
        self.assertTrue(subnet.delete.called)

    def test_get_subnet_name(self):
        subnet_name = self.subnet_srv._get_subnet_name('some_subnet')
        self.assertEquals(subnet_name, 'VPC Name: some_subnet')

    def test_get_vpc_subnets(self):
        # arrange
        subnet1 = Mock()
        subnet2 = Mock()
        vpc = Mock()
        vpc.subnets.all = Mock(return_value=[subnet1, subnet2])

        # act
        subnets = self.subnet_srv.get_vpc_subnets(vpc)

        # assert
        vpc.subnets.all.assert_called_once()
        self.assertTrue(subnet1 in subnets)
        self.assertTrue(subnet2 in subnets)
        self.assertEquals(len(subnets), 2)

    def test_get_vpc_subnets_throw_if_empty(self):
        # arrange
        vpc = Mock()
        vpc.id = "123"
        vpc.subnets.all = Mock(return_value=[])
        # act
        with self.assertRaises(Exception) as error:
            self.subnet_srv.get_vpc_subnets(vpc)
        # assert
        vpc.subnets.all.assert_called_once()
        self.assertEqual(error.exception.message, 'The given VPC(123) has no subnets')

    def test_get_first_or_none_subnet_from_vpc_returns_first(self):
        # arrange
        subnet1 = Mock()
        subnet2 = Mock()
        vpc = Mock()
        vpc.subnets.all = Mock(return_value=[subnet1, subnet2])

        # act
        subnet_result = self.subnet_srv.get_first_or_none_subnet_from_vpc(vpc=vpc)

        # assert
        vpc.subnets.all.assert_called_once()
        self.assertEquals(subnet1, subnet_result)

    def test_set_subnet_route_table(self):
        # arrange
        ec2_client = Mock()
        # act
        self.subnet_srv.set_subnet_route_table(ec2_client=ec2_client, subnet_id="123", route_table_id="456")
        # assert
        ec2_client.associate_route_table.assert_called_with(RouteTableId="456", SubnetId="123")

    def test_create_subnet_nowait(self):
        # Act
        self.subnet_srv.create_subnet_nowait(self.vpc, "1.2.3.4/24", "zoneA")
        # Assert
        self.vpc.create_subnet.assert_called_once_with(CidrBlock="1.2.3.4/24", AvailabilityZone="zoneA")

    def test_get_first_or_none_subnet_from_vpc__returns_none(self):
        # Arrange
        self.vpc.subnets.all = Mock(return_value=[])
        # Act
        subnet = self.subnet_srv.get_first_or_none_subnet_from_vpc(self.vpc)
        # Assert
        self.assertEqual(subnet, None)

    def test_get_first_or_none_subnet_from_vpc__returns_by_cidr(self):
        # Arrange
        s = Mock()
        s.cidr_block = "1.2.3.4/24"
        self.vpc.subnets.all = Mock(return_value=[s, Mock()])
        # Act
        subnet = self.subnet_srv.get_first_or_none_subnet_from_vpc(self.vpc, "1.2.3.4/24")
        # Assert
        self.assertEqual(subnet, s)

    def test_unset_subnet_route_table(self):
        ec2_client = Mock()
        subnet_id = Mock()
        association_id = Mock()
        table_id = Mock()
        result = {'RouteTables': [
            {'Associations': [
                {'SubnetId': Mock(),
                 'RouteTableAssociationId': Mock(),
                 'RouteTableId': Mock()
                 },
                {'SubnetId': subnet_id,
                 'RouteTableAssociationId': association_id,
                 'RouteTableId': table_id
                 }
            ]}
        ]}
        ec2_client.describe_route_tables.return_value = result

        self.assertEquals(self.subnet_srv.unset_subnet_route_table(ec2_client, subnet_id), table_id)
        ec2_client.describe_route_tables.assert_called_once_with(
            Filters=[{'Name': 'association.subnet-id', 'Values': [subnet_id, ]}, ])
        ec2_client.disassociate_route_table.assert_called_once_with(AssociationId=association_id)

    def test_get_nat_gateway_id_with_int_ip(self):
        ec2_client = Mock()
        subnet_id = Mock()
        int_ip = Mock()
        gateway_id = Mock()
        result = {'NatGateways': [
            {'NatGatewayAddresses': [
                {'PrivateIp': Mock()},
                {'PrivateIp': Mock()}
            ],
                'NatGatewayId': Mock()},
            {'NatGatewayAddresses': [
                {'PrivateIp': Mock()},
                {'PrivateIp': int_ip}
            ],
                'NatGatewayId': gateway_id}
        ]}

        ec2_client.describe_nat_gateways.return_value = result
        self.assertEquals(self.subnet_srv.get_nat_gateway_id_with_int_ip(ec2_client, subnet_id, int_ip), gateway_id)
        ec2_client.describe_nat_gateways.assert_called_once_with(Filters=[{'Name': 'subnet-id', 'Values': [subnet_id]}])

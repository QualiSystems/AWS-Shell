from unittest import TestCase

from mock import Mock, call

from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter


class TestVPCService(TestCase):
    def setUp(self):
        self.tag_service = Mock()
        self.tags = Mock()
        self.tag_service.get_default_tags = Mock(return_value=self.tags)
        self.subnet_service = Mock()
        self.logger = Mock()
        self.aws_ec2_datamodel = Mock()
        self.ec2_client= Mock()
        self.ec2_session = Mock()
        self.vpc = Mock()
        self.vpc_id = Mock()
        self.ec2_session.create_vpc = Mock(return_value=self.vpc)
        self.ec2_session.Vpc = Mock(return_value=self.vpc)
        self.s3_session = Mock()
        self.reservation = Mock()
        self.cidr = Mock()
        self.vpc_waiter = Mock()
        self.vpc_peering_waiter = Mock()
        self.instance_service = Mock()
        self.sg_service = Mock()
        self.route_table_service = Mock()
        self.traffic_mirror_service = Mock()
        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service,
                                      instance_service=self.instance_service,
                                      vpc_waiter=self.vpc_waiter,
                                      vpc_peering_waiter=self.vpc_peering_waiter,
                                      sg_service=self.sg_service,
                                      route_table_service=self.route_table_service,
                                      traffic_mirror_service=self.traffic_mirror_service)

    def test_get_all_internet_gateways(self):
        internet_gate = Mock()
        self.vpc.internet_gateways = Mock()
        self.vpc.internet_gateways.all = Mock(return_value=[internet_gate])
        res = self.vpc_service.get_all_internet_gateways(self.vpc)

        self.assertEquals(res, [internet_gate])

    def test_remove_all_internet_gateways(self):
        internet_gate = Mock()

        self.vpc.internet_gateways = Mock()
        self.vpc.internet_gateways.all = Mock(return_value=[internet_gate])
        self.vpc_service.remove_all_internet_gateways(self.vpc)

        internet_gate.detach_from_vpc.assert_called_with(VpcId=self.vpc.id)
        self.assertTrue(internet_gate.delete.called)


    def test_create_and_attach_internet_gateway(self):

        internet_gate = Mock()
        internet_gate.id = 'super_id'
        self.ec2_session.create_internet_gateway = Mock(return_value=internet_gate)

        internet_gateway_id = self.vpc_service.create_and_attach_internet_gateway(self.ec2_session, self.vpc, self.reservation)

        self.assertTrue(self.ec2_session.create_internet_gateway.called)
        self.tag_service.get_default_tags.assert_called_once_with("IGW {0}".format(self.reservation.reservation_id),self.reservation)
        self.tag_service.set_ec2_resource_tags.assert_called_once_with(resource=internet_gate, tags=self.tag_service.get_default_tags())
        self.assertEqual(internet_gateway_id, internet_gate.id)

    def test_create_vpc_for_reservation(self):
        vpc = self.vpc_service.create_vpc_for_reservation(self.ec2_session, self.reservation, self.cidr)
        vpc_name = self.vpc_service.VPC_RESERVATION.format(self.reservation.reservation_id)

        self.vpc_waiter.wait.assert_called_once_with(vpc=vpc, state=self.vpc_waiter.AVAILABLE)
        self.assertEqual(self.vpc, vpc)
        self.ec2_session.create_vpc.assert_called_once_with(CidrBlock=self.cidr)
        self.tag_service.get_default_tags.assert_called_once_with(vpc_name, self.reservation)
        self.tag_service.set_ec2_resource_tags.assert_called_once_with(self.vpc, self.tags)


    def test_find_vpc_for_reservation(self):
        self.ec2_session.vpcs = Mock()
        self.ec2_session.vpcs.filter = Mock(return_value=[self.vpc])
        vpc = self.vpc_service.find_vpc_for_reservation(self.ec2_session, self.reservation)
        self.assertEqual(vpc, self.vpc)

    def test_find_vpc_for_reservation_no_vpc(self):
        self.ec2_session.vpcs = Mock()
        self.ec2_session.vpcs.filter = Mock(return_value=[])
        vpc = self.vpc_service.find_vpc_for_reservation(self.ec2_session, self.reservation)
        self.assertIsNone(vpc)

    def test_find_vpc_for_reservation_too_many(self):
        self.ec2_session.vpcs = Mock()
        self.ec2_session.vpcs.filter = Mock(return_value=[1, 2])
        self.assertRaises(ValueError, self.vpc_service.find_vpc_for_reservation, self.ec2_session, self.reservation)

    def test_peer_vpc(self):
        def change_to_active(vpc_peering_connection):
            vpc_peering_connection.status['Code'] = VpcPeeringConnectionWaiter.ACTIVE

        vpc1 = Mock()
        vpc2 = Mock()
        peered = Mock()
        peered.status = {'Code': VpcPeeringConnectionWaiter.PENDING_ACCEPTANCE}
        peered.accept = Mock(side_effect=change_to_active(peered))
        self.ec2_session.create_vpc_peering_connection = Mock(return_value=peered)

        reservation_model = Mock()

        res = self.vpc_service.peer_vpcs(self.ec2_session, vpc1, vpc2, reservation_model,Mock())

        self.ec2_session.create_vpc_peering_connection.assert_called_once_with(VpcId=vpc1, PeerVpcId=vpc2)
        self.assertEqual(peered.status['Code'], VpcPeeringConnectionWaiter.ACTIVE)
        self.assertEqual(res, peered.id)

    def test_remove_all_peering(self):
        peering = Mock()
        peering.status = {'Code': 'ok'}
        peering1 = Mock()
        peering1.status = {'Code': 'failed'}
        peering2 = Mock()
        peering2.status = {'Code': 'aa'}
        self.vpc.accepted_vpc_peering_connections = Mock()
        self.vpc.accepted_vpc_peering_connections.all = Mock(return_value=[peering, peering1, peering2])

        res = self.vpc_service.remove_all_peering(self.vpc)

        self.assertIsNotNone(res)
        self.assertTrue(peering.delete.called)
        self.assertFalse(peering1.delete.called)
        self.assertTrue(peering2.delete.called)

    def test_remove_all_sgs(self):
        sg = Mock()
        self.vpc.security_groups = Mock()
        self.vpc.security_groups.all = Mock(return_value=[sg])

        res = self.vpc_service.remove_all_security_groups(self.vpc, self.reservation.reservation_id )

        self.assertIsNotNone(res)
        self.sg_service.delete_security_group.assert_called_once_with(sg)

    # When a trying to delete security group(isolated) and it is referenced in another's group rule.
    # we get resource sg-XXXXXX has a dependent object, so to fix that , isolated group shall be deleted last.
    def test_remove_all_sgs_isolated_group_removed_last(self):
        sg = Mock()
        sg.group_name = 'dummy'
        isolated_sg = Mock()
        isolated_sg.group_name = self.sg_service.sandbox_isolated_sg_name(self.reservation.reservation_id)
        isolated_at_start_sgs = [isolated_sg, sg]
        isolated_at_end_sgs_calls = [call(sg), call(isolated_sg)]

        self.vpc.security_groups = Mock()
        self.vpc.security_groups.all = Mock(return_value=isolated_at_start_sgs)

        res = self.vpc_service.remove_all_security_groups(self.vpc, self.reservation.reservation_id )

        self.assertIsNotNone(res)
        self.sg_service.delete_security_group.assert_has_calls(isolated_at_end_sgs_calls, any_order=False)

    def test_remove_subnets(self):
        subnet = Mock()
        self.vpc.subnets = Mock()
        self.vpc.subnets.all = Mock(return_value=[subnet])

        res = self.vpc_service.remove_all_subnets(self.vpc)

        self.assertIsNotNone(res)
        self.subnet_service.delete_subnet.assert_called_once_with(subnet)

    def test_delete_all_instances(self):
        instance = Mock()
        self.vpc.instances = Mock()
        self.vpc.instances.all = Mock(return_value=[instance])

        res = self.vpc_service.delete_all_instances(self.vpc)

        self.assertIsNotNone(res)
        self.instance_service.terminate_instances.assert_called_once_with([instance])

    def test_delete_vpc(self):
        res = self.vpc_service.delete_vpc(self.vpc)

        self.assertTrue(self.vpc.delete.called)
        self.assertIsNotNone(res)

    def test_get_or_create_subnet_for_vpc_1(self): # Scenario(1): Get
        # Arrange
        subnet = Mock()
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=subnet)
        # Act
        result = self.vpc_service.get_or_create_subnet_for_vpc(reservation=self.reservation,
                                                               cidr="1.2.3.4/24", alias="MySubnet",
                                                               vpc=self.vpc,
                                                               ec2_client=self.ec2_client,
                                                               aws_ec2_datamodel=self.aws_ec2_datamodel,
                                                               logger=self.logger)
        # Assert
        self.assertEqual(result, subnet)

    def test_get_or_create_subnet_for_vpc_2(self): # Scenario(2): Create
        # Arrange
        subnet = Mock()
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=None)
        self.reservation.reservation_id = "123"
        self.vpc_service.get_or_pick_availability_zone = Mock(return_value="MyZone")
        self.subnet_service.create_subnet_for_vpc = Mock(return_value=subnet)
        # Act
        result = self.vpc_service.get_or_create_subnet_for_vpc(reservation=self.reservation,
                                                               cidr="1.2.3.4/24", alias="MySubnet",
                                                               vpc=self.vpc,
                                                               ec2_client=self.ec2_client,
                                                               aws_ec2_datamodel=self.aws_ec2_datamodel,
                                                               logger=self.logger)
        # Assert
        self.assertEqual(result, subnet)
        self.subnet_service.create_subnet_for_vpc.assert_called_once_with(
            vpc=self.vpc,
            cidr="1.2.3.4/24",
            subnet_name="MySubnet Reservation: 123",
            availability_zone="MyZone",
            reservation=self.reservation)

    def test_get_or_create_private_route_table_1(self): # Scenario(1): Get
        # Arrange
        table = Mock()
        self.route_table_service.get_route_table = Mock(return_value=table)
        # Act
        result = self.vpc_service.get_or_create_private_route_table(ec2_session=self.ec2_session, reservation=self.reservation,
                                                           vpc_id=self.vpc_id)
        # Assert
        self.assertEqual(result, table)

    def test_get_or_create_private_route_table_2(self): # Scenario(2): Create
        # Arrange
        table = Mock()
        self.reservation.reservation_id = "123"
        self.route_table_service.get_route_table = Mock(return_value=None)
        self.route_table_service.create_route_table = Mock(return_value=table)
        # Act
        result = self.vpc_service.get_or_create_private_route_table(ec2_session=self.ec2_session,
                                                                    reservation=self.reservation,
                                                                    vpc_id=self.vpc_id)
        # Assert
        self.assertEqual(result, table)
        self.route_table_service.create_route_table.assert_called_once_with(
            self.ec2_session,
            self.reservation,
            self.vpc_id,
            "Private RoutingTable Reservation: 123"
        )

    def test_get_or_throw_private_route_table(self):
        # Arrange
        self.route_table_service.get_route_table = Mock(return_value=None)
        # Act
        with self.assertRaises(Exception) as error:
            self.vpc_service.get_or_throw_private_route_table(ec2_session=self.ec2_session, reservation=self.reservation,
                                                              vpc_id=self.vpc_id)
        # Assert
        self.assertEqual(error.exception.message, "Routing table for non-public subnet was not found")

    def test_get_vpc_cidr(self):
        # Arrange
        self.vpc.cidr_block = "1.2.3.4/24"
        # Act
        result = self.vpc_service.get_vpc_cidr(ec2_session=self.ec2_session, vpc_id=self.vpc_id)
        # Assert
        self.assertEqual(result, "1.2.3.4/24")

    def test_get_or_pick_availability_zone_1(self): #Scenario(1): from existing subnet
        # Arrange
        subnet = Mock()
        subnet.availability_zone = "z"
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=subnet)
        # Act
        result = self.vpc_service.get_or_pick_availability_zone(ec2_client=self.ec2_client, vpc=self.vpc,
                                                       aws_ec2_datamodel=self.aws_ec2_datamodel)
        # Assert
        self.assertEqual(result, "z")

    def test_get_or_pick_availability_zone_2(self):  # Scenario(2): from available zones list
        # Arrange
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=None)
        self.ec2_client.describe_availability_zones = Mock(return_value={"AvailabilityZones":[{"ZoneName":"z"}]})
        # Act
        result = self.vpc_service.get_or_pick_availability_zone(ec2_client=self.ec2_client, vpc=self.vpc,
                                                                aws_ec2_datamodel=self.aws_ec2_datamodel)
        # Assert
        self.assertEqual(result, "z")

    def test_get_or_pick_availability_zone_3(self):  # Scenario(3): no available zone
        # Arrange
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=None)
        self.ec2_client.describe_availability_zones = Mock(return_value=None)
        # Act
        with self.assertRaises(Exception) as error:
            self.vpc_service.get_or_pick_availability_zone(ec2_client=self.ec2_client, vpc=self.vpc,
                                                           aws_ec2_datamodel=self.aws_ec2_datamodel)
        # Assert
        self.assertEqual(error.exception.message, "No AvailabilityZone is available for this vpc")

    def test_remove_custom_route_tables(self):
        # Arrange
        tables = [Mock(), Mock()]
        self.vpc.id = "123"
        self.route_table_service.get_custom_route_tables = Mock(return_value=tables)
        # Act
        result = self.vpc_service.remove_custom_route_tables(ec2_session=self.ec2_session, vpc=self.vpc)
        # Assert
        self.assertTrue(result)
        self.route_table_service.delete_table.assert_any_call(tables[0])
        self.route_table_service.delete_table.assert_any_call(tables[1])

    def test_set_main_route_table_tags(self):
        # Arrange
        table = Mock()
        tags = Mock()
        self.reservation.reservation_id = "123"
        self.tag_service.get_default_tags = Mock(return_value=tags)
        # Act
        self.vpc_service.set_main_route_table_tags(main_route_table=table, reservation=self.reservation)
        # Assert
        self.tag_service.get_default_tags.assert_called_once_with("Main RoutingTable Reservation: 123", self.reservation)
        self.tag_service.set_ec2_resource_tags.assert_called_once_with(table, tags)
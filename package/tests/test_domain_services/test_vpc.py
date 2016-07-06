from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter


class TestVPCService(TestCase):
    def setUp(self):
        self.tag_service = Mock()
        self.tags = Mock()
        self.tag_service.get_default_tags = Mock(return_value=self.tags)
        self.subnet_service = Mock()
        self.ec2_session = Mock()
        self.vpc = Mock()
        self.ec2_session.create_vpc = Mock(return_value=self.vpc)
        self.s3_session = Mock()
        self.reservation = Mock()
        self.cidr = Mock()
        self.vpc_waiter = Mock()
        self.vpc_peering_waiter = Mock()
        self.instance_service = Mock()
        self.sg_service = Mock()
        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service,
                                      instance_service=self.instance_service,
                                      vpc_waiter=self.vpc_waiter,
                                      vpc_peering_waiter=self.vpc_peering_waiter,
                                      sg_service=self.sg_service)

    def test_create_vpc_for_reservation(self):
        vpc = self.vpc_service.create_vpc_for_reservation(self.ec2_session, self.reservation, self.cidr)

        vpc_name = self.vpc_service.VPC_RESERVATION.format(self.reservation)

        self.assertTrue(self.vpc_waiter.wait.called_with(vpc, 'available'))
        self.assertEqual(self.vpc, vpc)
        self.assertTrue(self.ec2_session.create_vpc.called_with(self.cidr))
        self.assertTrue(
            self.tag_service.get_default_tags.called_with(vpc_name,
                                                          self.reservation))
        self.assertTrue(self.tag_service.set_ec2_resource_tags.called_with(self.vpc, self.tags))
        self.assertTrue(self.subnet_service.create_subnet_for_vpc(self.vpc, self.cidr, vpc_name))

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

        res = self.vpc_service.peer_vpcs(self.ec2_session, vpc1, vpc2)

        self.assertTrue(self.ec2_session.create_vpc_peering_connection.called_with(vpc1, vpc2))
        self.assertEquals(peered.status['Code'], VpcPeeringConnectionWaiter.ACTIVE)
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

        self.assertTrue(res)
        self.assertTrue(peering.delete.called)
        self.assertFalse(peering1.delete.called)
        self.assertTrue(peering2.delete.called)

    def test_remove_all_sgs(self):
        sg = Mock()
        self.vpc.security_groups = Mock()
        self.vpc.security_groups.all = Mock(return_value=[sg])

        res = self.vpc_service.remove_all_security_groups(self.vpc)

        self.assertTrue(res)
        self.assertTrue(self.sg_service.delete_security_group.called_with(sg))

    def test_remove_subnets(self):
        subnet = Mock()
        self.vpc.subnets = Mock()
        self.vpc.subnets.all = Mock(return_value=[subnet])

        res = self.vpc_service.remove_all_subnets(self.vpc)

        self.assertTrue(res)
        self.assertTrue(self.subnet_service.delete_subnet.called_with(subnet))

    def test_delete_all_instances(self):
        instance = Mock()
        self.vpc.instances = Mock()
        self.vpc.instances.all = Mock(return_value=[instance])

        res = self.vpc_service.delete_all_instances(self.vpc)

        self.assertTrue(res)
        self.assertTrue(self.instance_service.terminate_instances.called_with([instance]))

    def test_delete_vpc(self):
        res = self.vpc_service.delete_vpc(self.vpc)

        self.assertTrue(self.vpc.delete.called)
        self.assertTrue(res)
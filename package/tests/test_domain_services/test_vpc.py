from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService


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
        self.reservation_id = 'id'
        self.cidr = Mock()
        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service)

    def test_create_vpc_for_reservation(self):
        vpc = self.vpc_service.create_vpc_for_reservation(self.ec2_session, self.reservation_id, self.cidr)

        vpc_name = self.vpc_service.VPC_RESERVATION.format(self.reservation_id)

        self.assertEqual(self.vpc, vpc)
        self.assertTrue(self.ec2_session.create_vpc.called_with(self.cidr))
        self.assertTrue(
            self.tag_service.get_default_tags.called_with(vpc_name,
                                                          self.reservation_id))
        self.assertTrue(self.tag_service.set_ec2_resource_tags.called_with(self.vpc, self.tags))
        self.assertTrue(self.subnet_service.create_subnet_for_vpc(self.vpc, self.cidr, vpc_name))

    def test_find_vpc_for_reservation(self):
        self.ec2_session.vpcs = Mock()
        self.ec2_session.vpcs.filter = Mock(return_value=[self.vpc])
        vpc = self.vpc_service.find_vpc_for_reservation(self.ec2_session, self.reservation_id)
        self.assertEqual(vpc, self.vpc)

    def test_find_vpc_for_reservation_no_vpc(self):
        self.ec2_session.vpcs = Mock()
        self.ec2_session.vpcs.filter = Mock(return_value=[])
        vpc = self.vpc_service.find_vpc_for_reservation(self.ec2_session, self.reservation_id)
        self.assertIsNone(vpc)

    def test_find_vpc_for_reservation_too_many(self):
        self.ec2_session.vpcs = Mock()
        self.ec2_session.vpcs.filter = Mock(return_value=[1,2])
        self.assertRaises(ValueError, self.vpc_service.find_vpc_for_reservation, self.ec2_session, self.reservation_id)

    def test_peer_vpc(self):
        vpc1 = Mock()
        vpc2 = Mock()
        peered = Mock()
        self.ec2_session.create_vpc_peering_connection = Mock(return_value=peered)

        res = self.vpc_service.peer_vpcs(self.ec2_session, vpc1, vpc2)

        self.assertTrue(self.ec2_session.create_vpc_peering_connection.called_with(vpc1, vpc2))
        self.assertEqual(res, peered.id)
from _ast import Eq
from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupSandboxInfraOperation
from cloudshell.cp.core.models import PrepareCloudInfra


class TestCleanupSandboxInfra(TestCase):
    def setUp(self):
        self.vpc_serv = Mock()
        self.key_pair_serv = Mock()
        self.s3_session = Mock()
        self.ec2_session = Mock()
        self.aws_ec2_data_model = Mock()
        self.reservation_id = Mock()
        self.route_table_service = Mock()
        self.traffic_mirror_service = Mock()
        self.cleanup_operation = CleanupSandboxInfraOperation(self.vpc_serv, self.key_pair_serv,
                                                              self.route_table_service, self.traffic_mirror_service)

    def test_cleanup(self):
        self.route_table_service.get_all_route_tables = Mock(return_value=[Mock(), Mock()])
        vpc = self.vpc_serv.find_vpc_for_reservation()

        self.cleanup_operation.cleanup(ec2_session=self.ec2_session,
                                       s3_session=self.s3_session,
                                       aws_ec2_data_model=self.aws_ec2_data_model,
                                       reservation_id=self.reservation_id,
                                       logger=Mock(),
                                       actions=[PrepareCloudInfra()],
                                       ec2_client=Mock())

        self.assertTrue(self.vpc_serv.find_vpc_for_reservation.called_with(self.ec2_session, self.reservation_id))
        self.assertTrue(self.key_pair_serv.remove_key_pair_for_reservation_in_s3.called_with(self.s3_session,
                                                                                             self.aws_ec2_data_model,
                                                                                             self.reservation_id))
        self.assertTrue(self.vpc_serv.delete_all_instances.called_with(vpc))
        self.assertTrue(self.vpc_serv.remove_all_security_groups.called_with(vpc))
        self.assertTrue(self.vpc_serv.remove_all_subnets.called_with(vpc))
        self.assertTrue(self.vpc_serv.remove_all_peering.called_with(vpc))
        self.assertTrue(self.vpc_serv.delete_vpc.called_with(vpc))
        self.route_table_service.get_all_route_tables.assert_called_once_with(ec2_session=self.ec2_session,
                                                                              vpc_id=self.aws_ec2_data_model.aws_management_vpc_id)
        self.assertEquals(self.route_table_service.delete_blackhole_routes.call_count, 2)

    def test_cleanup_no_vpc(self):
        vpc_serv = Mock()
        vpc_serv.find_vpc_for_reservation = Mock(return_value=None)
        result = CleanupSandboxInfraOperation(vpc_serv, self.key_pair_serv, self.route_table_service, self.traffic_mirror_service) \
            .cleanup(
                ec2_session=self.ec2_session,
                s3_session=self.s3_session,
                aws_ec2_data_model=self.aws_ec2_data_model,
                reservation_id=self.reservation_id,
                ec2_client=Mock(),
                actions=[PrepareCloudInfra()],
                logger=Mock())

        self.assertFalse(result.success)

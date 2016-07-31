from unittest import TestCase
from mock import Mock, patch

from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter

vpc_peering_connection = Mock()
vpc_peering_connection.status = {'Code': ''}


class helper:
    @staticmethod
    def change_to_initiating_request(x):
        vpc_peering_connection.status['Code'] = VpcPeeringConnectionWaiter.INITIATING_REQUEST

    @staticmethod
    def change_to_pending_acceptance(x):
        vpc_peering_connection.status['Code'] = VpcPeeringConnectionWaiter.PENDING_ACCEPTANCE

    @staticmethod
    def change_to_active(x):
        vpc_peering_connection.status['Code'] = VpcPeeringConnectionWaiter.ACTIVE

    @staticmethod
    def change_to_failed(x):
        vpc_peering_connection.status['Code'] = VpcPeeringConnectionWaiter.FAILED


class TestInstanceWaiter(TestCase):
    def setUp(self):
        self.vpc_peering_connection_waiter = VpcPeeringConnectionWaiter(1, 0.02)
        # self.vpc_peering_connection = Mock()

    @patch('time.sleep', helper.change_to_active)
    def test_waiter(self):
        helper.change_to_pending_acceptance(Mock())

        peering_conn = self.vpc_peering_connection_waiter.wait(vpc_peering_connection,
                                                               VpcPeeringConnectionWaiter.ACTIVE)
        self.assertEqual(peering_conn, vpc_peering_connection)
        self.assertEqual(peering_conn.reload.call_count, 1)

    def test_waiter_timeout(self):
        helper.change_to_pending_acceptance(Mock())
        self.assertRaises(Exception, self.vpc_peering_connection_waiter.wait, vpc_peering_connection,
                          VpcPeeringConnectionWaiter.ACTIVE)

    @patch('time.sleep', helper.change_to_failed)
    def test_waiter_throw_on_error_state(self):
        helper.change_to_pending_acceptance(Mock())
        self.assertRaises(Exception, self.vpc_peering_connection_waiter.wait, vpc_peering_connection,
                          VpcPeeringConnectionWaiter.ACTIVE)

from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.waiters.vpc import VPCWaiter


class TestVPCWaiter(TestCase):
    def setUp(self):
        self.vpc_waiter = VPCWaiter(1, 0.02)

    def test_wait_none(self):
        self.assertRaises(ValueError, self.vpc_waiter.wait, None, VPCWaiter.PENDING)
        self.assertRaises(ValueError, self.vpc_waiter.wait, Mock(), 'bla')
        self.assertRaises(Exception, self.vpc_waiter.wait, Mock(), VPCWaiter.PENDING)

    def test_wait(self):
        vpc = Mock()

        def reload():
            vpc.state = VPCWaiter.AVAILABLE

        vpc.reload = reload
        res = self.vpc_waiter.wait(vpc, VPCWaiter.AVAILABLE)
        self.assertEqual(res.state, VPCWaiter.AVAILABLE)

from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter


class TestSubnetWaiter(TestCase):
    def setUp(self):
        self.vpc_waiter = SubnetWaiter(1, 0.02)

    def test_wait_none(self):
        self.assertRaises(ValueError, self.vpc_waiter.wait, None, SubnetWaiter.PENDING)
        self.assertRaises(ValueError, self.vpc_waiter.wait, Mock(), 'bla')
        self.assertRaises(Exception, self.vpc_waiter.wait, Mock(), SubnetWaiter.PENDING)

    def test_wait(self):
        vpc = Mock()

        def reload():
            vpc.state = SubnetWaiter.AVAILABLE

        vpc.reload = reload
        res = self.vpc_waiter.wait(vpc, SubnetWaiter.AVAILABLE)
        self.assertEqual(res.state, SubnetWaiter.AVAILABLE)

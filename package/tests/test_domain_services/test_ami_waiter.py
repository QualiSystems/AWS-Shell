from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.waiters.ami import AMIWaiter


class TestSubnetWaiter(TestCase):
    def setUp(self):
        self.vpc_waiter = AMIWaiter(1, 0.02)

    def test_wait_none(self):
        self.assertRaises(ValueError, self.vpc_waiter.wait, None, AMIWaiter.PENDING)
        self.assertRaises(ValueError, self.vpc_waiter.wait, Mock(), 'bla')
        self.assertRaises(Exception, self.vpc_waiter.wait, Mock(), AMIWaiter.PENDING)

    def test_wait(self):
        vpc = Mock()

        def reload():
            vpc.state = AMIWaiter.AVAILABLE

        vpc.reload = reload
        res = self.vpc_waiter.wait(vpc, AMIWaiter.AVAILABLE)
        self.assertEqual(res.state, AMIWaiter.AVAILABLE)

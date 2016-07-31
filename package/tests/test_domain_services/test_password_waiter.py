from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.waiters.password import PasswordWaiter


class TestPasswordWaiter(TestCase):
    def setUp(self):
        self.pass_waiter = PasswordWaiter(0.5, 0.02)

    def test_wait_none(self):
        self.assertRaises(ValueError, self.pass_waiter.wait, None)

    def test_wait_timeout(self):
        instance = Mock()
        instance.password_data = Mock(return_value={'PasswordData': ''})
        self.assertRaises(Exception, self.pass_waiter.wait, instance)

    def test_wait(self):
        instance = Mock()
        instance.password_data = Mock()
        instance.password_data.side_effect = [{'PasswordData': ''}, {'PasswordData': 'password'}]
        res = self.pass_waiter.wait(instance)
        self.assertEqual(res, 'password')

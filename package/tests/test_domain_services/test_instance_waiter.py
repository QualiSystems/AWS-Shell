from unittest import TestCase
from mock import Mock, patch

from cloudshell.cp.aws.domain.services.task_manager.instance_waiter import EC2InstanceWaiter

instance = Mock()
instance.state = {'Name': ''}


class helper:
    @staticmethod
    def change_to_terminate(a):
        instance.state['Name'] = EC2InstanceWaiter.TERMINATED

    @staticmethod
    def change_to_stopped(a):
        instance.state['Name'] = EC2InstanceWaiter.STOPPED

    @staticmethod
    def change_to_running(a):
        instance.state['Name'] = EC2InstanceWaiter.RUNNING

    @staticmethod
    def change_to_stopping(a):
        instance.state['Name'] = EC2InstanceWaiter.STOPPING

    @staticmethod
    def change_to_pending(a):
        instance.state['Name'] = EC2InstanceWaiter.PENDING


class TestInstanceWaiter(TestCase):
    def setUp(self):
        self.instance_waiter = EC2InstanceWaiter(1, 0.02)
        self.instance = Mock()

    @patch('time.sleep', helper.change_to_stopped)
    def test_waiter(self):
        helper.change_to_running(Mock())
        inst = self.instance_waiter.wait(instance, EC2InstanceWaiter.STOPPED)
        self.assertEqual(inst, instance)
        self.assertEqual(inst.reload.call_count, 1)

    def test_waiter_timeout(self):
        helper.change_to_running(Mock())
        self.assertRaises(Exception, self.instance_waiter.wait, instance, EC2InstanceWaiter.STOPPED)

    def test_waiter_load(self):
        helper.change_to_stopped(Mock())
        inst = self.instance_waiter.wait(instance, EC2InstanceWaiter.STOPPED, True)
        self.assertEqual(inst, instance)
        self.assertTrue(inst.reload.call_count, 2)

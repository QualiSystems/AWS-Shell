from unittest import TestCase
from mock import Mock

from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation


class TestPowerOperations(TestCase):
    def setUp(self):
        self.aws_ec2_service = Mock()
        self.instance = Mock()
        self.aws_ec2_service.get_instance_by_id = Mock(return_value=self.instance)
        self.power_operations = PowerOperation(self.aws_ec2_service, Mock())
        self.ec2_session = Mock()

    def test_power_on_already_powered_on(self):
        self.instance.state = {'Name': 'running'}
        result = self.power_operations.power_on(self.ec2_session, 'id')
        self.assertTrue(result)
        self.assertTrue(self.aws_ec2_service.get_instance_by_id.called_with(self.ec2_session, 'id'))
        self.assertFalse(self.instance.start.called)
        self.assertFalse(self.instance.wait_until_running.called)

    def test_power_on_instance_not_running(self):
        self.instance.state = {'Name': 'stopped'}
        result = self.power_operations.power_on(self.ec2_session, 'id')
        self.assertTrue(result)
        self.assertTrue(self.aws_ec2_service.get_instance_by_id.called_with(self.ec2_session, 'id'))
        self.assertTrue(self.instance.start.called)
        self.assertTrue(self.instance.wait_until_running.called)

    def test_power_off_already_stopped(self):
        self.instance.state = {'Name': 'stopped'}
        result = self.power_operations.power_off(self.ec2_session, 'id')
        self.assertTrue(result)
        self.assertTrue(self.aws_ec2_service.get_instance_by_id.called_with(self.ec2_session, 'id'))
        self.assertFalse(self.instance.stop.called)
        self.assertFalse(self.instance.wait_until_stopped.called)

    def test_power_off_already_stopped(self):
        self.instance.state = {'Name': 'running'}
        result = self.power_operations.power_off(self.ec2_session, 'id')
        self.assertTrue(result)
        self.assertTrue(self.aws_ec2_service.get_instance_by_id.called_with(self.ec2_session, 'id'))
        self.assertTrue(self.instance.stop.called)
        self.assertTrue(self.instance.wait_until_stopped.called)

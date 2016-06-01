from unittest import TestCase
from mock import Mock

from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation


class TestPowerOperations(TestCase):
    def setUp(self):
        self.aws_api = Mock()
        self.instance = Mock()
        self.aws_api.get_instance_by_id = Mock(return_value=self.instance)
        self.power_operations = PowerOperation(self.aws_api, Mock())
        self.ec2_session = Mock()

    def test_power_on(self):
        self.assertTrue(self.power_operations.power_on(self.ec2_session, 'id'))
        self.assertTrue(self.aws_api.get_instance_by_id.called_with(self.ec2_session, 'id'))

    def test_power_off(self):
        self.assertTrue(self.power_operations.power_off(self.ec2_session, 'id'))
        self.assertTrue(self.aws_api.get_instance_by_id.called_with(self.ec2_session, 'id'))


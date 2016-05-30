from unittest import TestCase

import jsonpickle
from mock import Mock
from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class TestAWSShell(TestCase):
    def setUp(self):
        self.aws_shell_api = AWSShell()

        self.aws_shell_api.credentials_manager = Mock()
        self.aws_shell_api.cloudshell_session_helper = Mock()
        self.aws_shell_api.aws_session_manager.get_ec2_session = Mock(return_value=Mock())

        self.command_context = Mock()
        self.command_context.resource = Mock()
        self.command_context.remote_endpoints = []

        self.command_context.connectivity = Mock()
        self.command_context.connectivity.server_address = Mock()
        self.command_context.connectivity.admin_auth_token = Mock()

        self.command_context.reservation = Mock()
        self.command_context.reservation.domain = Mock()

        self.command_context.remote_reservation = Mock()
        self.command_context.remote_reservation.domain = Mock()

        self.aws_shell_api.model_parser.convert_to_aws_resource_model = Mock(
            return_value=(AWSEc2CloudProviderResourceModel()))

    def test_deploying_ami_returns_deploy_result(self):
        name = 'my instance name'
        result = Mock()
        result.instance_id = 'my instance id'

        deploymock = DeployAWSEc2AMIInstanceResourceModel()
        deploymock.auto_power_on = "True"
        deploymock.auto_power_off = "True"
        deploymock.wait_for_ip = "True"
        deploymock.auto_delete = "True"
        deploymock.autoload = "True"
        deploymock.aws_ec2 = "some_name"

        self.aws_shell_api.model_parser.convert_to_deployment_resource_model = Mock(return_value=(deploymock, name))

        self.aws_shell_api.deploy_ami_operation.deploy = Mock(return_value=(result, name))

        aws_cloud_provider = AWSEc2CloudProviderResourceModel()

        res = self.aws_shell_api.deploy_ami(self.command_context, aws_cloud_provider)

        self.assertEqual(jsonpickle.decode(res)['vm_name'], name)
        self.assertEqual(jsonpickle.decode(res)['vm_uuid'], result.instance_id)
        self.assertEqual(jsonpickle.decode(res)['auto_power_on'], deploymock.auto_power_on)
        self.assertEqual(jsonpickle.decode(res)['auto_power_off'], deploymock.auto_power_off)
        self.assertEqual(jsonpickle.decode(res)['wait_for_ip'], deploymock.wait_for_ip)
        self.assertEqual(jsonpickle.decode(res)['auto_delete'], deploymock.auto_delete)
        self.assertEqual(jsonpickle.decode(res)['autoload'], deploymock.autoload)
        self.assertEqual(jsonpickle.decode(res)['cloud_provider_resource_name'], deploymock.aws_ec2)

    def test_power_on(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell_api.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell_api.power_management_operation.power_on = Mock(return_value=True)
        self.aws_shell_api.power_on_ami(self.command_context)

        self.assertTrue(
            self.aws_shell_api.power_management_operation.power_on.called_with(
                self.aws_shell_api.aws_session_manager.get_ec2_session(), 'id'))

    def test_power_off(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell_api.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell_api.power_management_operation.power_off = Mock(return_value=True)
        self.aws_shell_api.power_on_ami(self.command_context)

        self.assertTrue(
            self.aws_shell_api.power_management_operation.power_off.called_with(
                self.aws_shell_api.aws_session_manager.get_ec2_session(), 'id'))


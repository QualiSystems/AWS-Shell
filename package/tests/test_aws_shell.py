from unittest import TestCase

import jsonpickle
from mock import Mock
from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult


class TestAWSShell(TestCase):
    def setUp(self):
        self.aws_shell_api = AWSShell()

        self.aws_shell_api.credentials_manager = Mock()
        self.aws_shell_api.ec2_storage_service = Mock()
        self.aws_shell_api.ec2_instance_waiter = Mock()
        self.aws_shell_api.cloudshell_session_helper = Mock()
        self.aws_shell_api.aws_session_manager.get_ec2_session = Mock(return_value=Mock())
        self.aws_shell_api.aws_session_manager.get_s3_session = Mock(return_value=Mock())

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

        deploymock = DeployAWSEc2AMIInstanceResourceModel()
        deploymock.auto_power_on = "True"
        deploymock.auto_power_off = "True"
        deploymock.wait_for_ip = "True"
        deploymock.auto_delete = "True"
        deploymock.autoload = "True"
        deploymock.cloud_provider_resource = "some_name"

        result = DeployResult(vm_name=name,
                              vm_uuid='my instance id',
                              cloud_provider_resource_name=deploymock.cloud_provider_resource,
                              autoload=deploymock.autoload,
                              auto_delete=deploymock.auto_delete,
                              wait_for_ip=deploymock.wait_for_ip,
                              auto_power_on=deploymock.auto_power_on,
                              auto_power_off=deploymock.auto_power_off,
                              inbound_ports='',
                              outbound_ports='',
                              deployed_app_attributes=dict(),
                              deployed_app_address=None,
                              public_ip=None,
                              elastic_ip=None)


        self.aws_shell_api.model_parser.convert_to_deployment_resource_model = Mock(return_value=(deploymock, name))

        self.aws_shell_api.deploy_ami_operation.deploy = Mock(return_value=result)

        aws_cloud_provider = AWSEc2CloudProviderResourceModel()

        res = self.aws_shell_api.deploy_ami(self.command_context, aws_cloud_provider)

        decoded_res = jsonpickle.decode(res)
        self.assertEqual(decoded_res['vm_name'], name)
        self.assertEqual(decoded_res['vm_uuid'], result.vm_uuid)
        self.assertEqual(decoded_res['auto_power_on'], deploymock.auto_power_on)
        self.assertEqual(decoded_res['auto_power_off'], deploymock.auto_power_off)
        self.assertEqual(decoded_res['wait_for_ip'], deploymock.wait_for_ip)
        self.assertEqual(decoded_res['auto_delete'], deploymock.auto_delete)
        self.assertEqual(decoded_res['autoload'], deploymock.autoload)
        self.assertEqual(decoded_res['cloud_provider_resource_name'], deploymock.cloud_provider_resource)

    def test_cleanup_connectivity(self):
        self.aws_shell_api.clean_up_operation.cleanup = Mock(return_value=True)

        self.aws_shell_api.cleanup_connectivity(self.command_context)

        self.assertTrue(self.aws_shell_api.clean_up_operation.cleanup.called_with(
            self.aws_shell_api.aws_session_manager.get_ec2_session(),
            self.aws_shell_api.aws_session_manager.get_s3_session(),
            self.aws_shell_api.model_parser.convert_to_aws_resource_model().key_pairs_location,
            self.command_context.reservation.reservation_id
        ))

    def test_prepare_connectivity(self):
        req = '{"driverRequest": {"actions": [{"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356","actionTarget": null,"customActionAttributes": [{"attributeName": "Network","attributeValue": "10.0.0.0/24","type": "customAttribute"}],"type": "prepareNetwork"}]}}'
        self.aws_shell_api.prepare_connectivity_operation.prepare_connectivity = Mock(return_value=True)

        res = self.aws_shell_api.prepare_connectivity(self.command_context, req)

        self.assertTrue(self.aws_shell_api.prepare_connectivity_operation.prepare_connectivity.called_with(
            self.aws_shell_api.aws_session_manager.get_ec2_session(),
            self.aws_shell_api.aws_session_manager.get_s3_session(),
            self.command_context.reservation.reservation_id,
            self.aws_shell_api.model_parser.convert_to_aws_resource_model,
            DeployDataHolder(jsonpickle.decode(req)).driverRequest
        ))
        self.assertEqual(res, '{"driverResponse": {"actionResults": true}}')

    def test_prepare_connectivity_invalid_req(self):
        req = '{"aa": {"actions": [{"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356","actionTarget": null,"customActionAttributes": [{"attributeName": "Network","attributeValue": "10.0.0.0/24","type": "customAttribute"}],"type": "prepareNetwork"}]}}'
        self.aws_shell_api.prepare_connectivity_operation.prepare_connectivity = Mock(return_value=True)

        self.assertRaises(ValueError, self.aws_shell_api.prepare_connectivity, self.command_context, req)

    def test_delete_ami(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell_api.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell_api.delete_ami_operation.delete_instance = Mock(return_value=True)

        self.aws_shell_api.delete_ami(self.command_context)

        self.assertTrue(
            self.aws_shell_api.delete_ami_operation.delete_instance.called_with(
                self.aws_shell_api.aws_session_manager.get_ec2_session(), 'id'))

    def test_delete_ami_delete_resource(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell_api.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell_api.delete_ami_operation.delete_instance = Mock(return_value=True)

        self.aws_shell_api.delete_ami(self.command_context)

        self.assertTrue(
            self.aws_shell_api.delete_ami_operation.delete_instance.called_with(
                self.aws_shell_api.aws_session_manager.get_ec2_session(), 'id'))

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
        self.aws_shell_api.power_off_ami(self.command_context)

        self.assertTrue(
            self.aws_shell_api.power_management_operation.power_off.called_with(
                self.aws_shell_api.aws_session_manager.get_ec2_session(), 'id'))

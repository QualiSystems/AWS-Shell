from unittest import TestCase

import jsonpickle
from mock import Mock, patch, MagicMock
from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContextModel
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class TestAWSShell(TestCase):
    def setUp(self):
        self.aws_shell = AWSShell()

        self.aws_shell.credentials_manager = Mock()
        self.aws_shell.ec2_storage_service = Mock()
        self.aws_shell.ec2_instance_waiter = Mock()
        self.aws_shell.cloudshell_session_helper = Mock()
        self.aws_shell.aws_session_manager.get_ec2_session = Mock(return_value=Mock())
        self.aws_shell.aws_session_manager.get_s3_session = Mock(return_value=Mock())
        self.aws_shell.aws_session_manager.get_ec2_client = Mock(return_value=Mock())

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

        self.aws_shell.model_parser.convert_to_aws_resource_model = Mock(
                return_value=(AWSEc2CloudProviderResourceModel()))
        self.reservation_model = ReservationModel(self.command_context.reservation)
        self.aws_shell.model_parser.convert_to_reservation_model = Mock(
            return_value=self.reservation_model)

        self.expected_shell_context = Mock(spec=AwsShellContextModel)
        self.expected_shell_context.logger = Mock()
        self.expected_shell_context.cloudshell_session = Mock()
        self.expected_shell_context.aws_ec2_resource_model = Mock()
        self.expected_shell_context.aws_api = Mock()
        self.expected_shell_context.aws_api.ec2_session = Mock()
        self.expected_shell_context.aws_api.s3_session = Mock()
        self.expected_shell_context.aws_api.ec2_client = Mock()

        self.mock_context = Mock()
        self.mock_context.__enter__ = Mock(return_value=self.expected_shell_context)
        self.mock_context.__exit__ = Mock(return_value=False)

    def test_deploying_ami_returns_deploy_result(self):
        # arrange
        deploymock = DeployAWSEc2AMIInstanceResourceModel()
        deploymock.auto_power_off = "True"
        deploymock.wait_for_ip = "True"
        deploymock.auto_delete = "True"
        deploymock.autoload = "True"
        deploymock.cloud_provider = "some_name"
        deploymock.app_name = 'my instance name'

        result = DeployResult(vm_name=deploymock.app_name,
                              vm_uuid='my instance id',
                              cloud_provider_resource_name=deploymock.cloud_provider,
                              autoload=deploymock.autoload,
                              auto_delete=deploymock.auto_delete,
                              wait_for_ip=deploymock.wait_for_ip,
                              auto_power_off=deploymock.auto_power_off,
                              inbound_ports='',
                              outbound_ports='',
                              deployed_app_attributes=dict(),
                              deployed_app_address='',
                              public_ip='',
                              elastic_ip='')

        self.aws_shell.model_parser.convert_to_deployment_resource_model = Mock(return_value=deploymock)
        self.aws_shell.deploy_ami_operation.deploy = Mock(return_value=result)
        aws_cloud_provider = AWSEc2CloudProviderResourceModel()

        res = None
        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            res = self.aws_shell.deploy_ami(self.command_context, aws_cloud_provider)

        decoded_res = jsonpickle.decode(res)
        self.assertEqual(decoded_res['vm_name'], deploymock.app_name)
        self.assertEqual(decoded_res['vm_uuid'], result.vm_uuid)
        self.assertEqual(decoded_res['auto_power_off'], deploymock.auto_power_off)
        self.assertEqual(decoded_res['wait_for_ip'], deploymock.wait_for_ip)
        self.assertEqual(decoded_res['auto_delete'], deploymock.auto_delete)
        self.assertEqual(decoded_res['autoload'], deploymock.autoload)
        self.assertEqual(decoded_res['cloud_provider_resource_name'], deploymock.cloud_provider)
        self.aws_shell.deploy_ami_operation.deploy.assert_called_with(
                ec2_session=self.expected_shell_context.aws_api.ec2_session,
                s3_session=self.expected_shell_context.aws_api.s3_session,
                name=deploymock.app_name,
                reservation=self.reservation_model,
                aws_ec2_cp_resource_model=self.expected_shell_context.aws_ec2_resource_model,
                ami_deployment_model=deploymock,
                ec2_client=self.expected_shell_context.aws_api.ec2_client,
                logger=self.expected_shell_context.logger)

    def test_cleanup_connectivity(self):
        # prepare
        self.aws_shell.clean_up_operation.cleanup = Mock(return_value=True)

        result = None
        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            result = self.aws_shell.cleanup_connectivity(self.command_context)

        # assert
        self.aws_shell.clean_up_operation.cleanup.assert_called_with(
                ec2_client=self.expected_shell_context.aws_api.ec2_client,
                ec2_session=self.expected_shell_context.aws_api.ec2_session,
                s3_session=self.expected_shell_context.aws_api.s3_session,
                aws_ec2_data_model=self.expected_shell_context.aws_ec2_resource_model,
                reservation_id=self.command_context.reservation.reservation_id,
                logger=self.expected_shell_context.logger)
        self.assertEquals(result, '{"driverResponse": {"actionResults": [true]}}')

    def test_prepare_connectivity(self):
        # Assert
        req = '{"driverRequest": {"actions": [{"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356","actionTarget": null,"customActionAttributes": [{"attributeName": "Network","attributeValue": "10.0.0.0/24","type": "customAttribute"}],"type": "prepareNetwork"}]}}'
        self.aws_shell.prepare_connectivity_operation.prepare_connectivity = Mock(return_value=True)
        res = None
        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context
            with patch('cloudshell.cp.aws.aws_shell.DeployDataHolder') as deploy_data_holder:
                data_holder_mock = Mock()
                data_holder_mock.driverRequest = Mock()
                deploy_data_holder.return_value = data_holder_mock

                # Act
                res = self.aws_shell.prepare_connectivity(self.command_context, req)

            # Assert
            self.aws_shell.prepare_connectivity_operation.prepare_connectivity.assert_called_with(
                ec2_client=self.expected_shell_context.aws_api.ec2_client,
                ec2_session=self.expected_shell_context.aws_api.ec2_session,
                s3_session=self.expected_shell_context.aws_api.s3_session,
                reservation=self.reservation_model,
                aws_ec2_datamodel=self.expected_shell_context.aws_ec2_resource_model,
                request=data_holder_mock.driverRequest,
                logger=self.expected_shell_context.logger)
            self.assertEqual(res, '{"driverResponse": {"actionResults": true}}')

    def test_prepare_connectivity_invalid_req(self):
        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext'):
            req = '{"aa": {"actions": [{"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356","actionTarget": null,"customActionAttributes": [{"attributeName": "Network","attributeValue": "10.0.0.0/24","type": "customAttribute"}],"type": "prepareNetwork"}]}}'
            self.aws_shell.prepare_connectivity_operation.prepare_connectivity = Mock(return_value=True)

            self.assertRaises(ValueError, self.aws_shell.prepare_connectivity, self.command_context, req)

    def test_delete_instance(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell.delete_ami_operation.delete_instance = Mock(return_value=True)

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            self.aws_shell.delete_instance(self.command_context)

        self.aws_shell.delete_ami_operation.delete_instance.assert_called_with(
            logger=self.expected_shell_context.logger,
            ec2_session=self.expected_shell_context.aws_api.ec2_session,
            instance_id=deployed_model.vmdetails.uid)

    def test_power_on(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell.power_management_operation.power_on = Mock(return_value=True)

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            self.aws_shell.power_on_ami(self.command_context)

        self.aws_shell.power_management_operation.power_on.assert_called_with(
            ec2_session=self.expected_shell_context.aws_api.ec2_session,
            ami_id=deployed_model.vmdetails.uid)

    def test_power_off(self):
        deployed_model = DeployDataHolder({'vmdetails': {'uid': 'id'}})
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]
        self.aws_shell.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)
        self.aws_shell.power_management_operation.power_off = Mock(return_value=True)

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            self.aws_shell.power_off_ami(self.command_context)

        self.aws_shell.power_management_operation.power_off.assert_called_with(
            ec2_session=self.expected_shell_context.aws_api.ec2_session,
            ami_id=deployed_model.vmdetails.uid)

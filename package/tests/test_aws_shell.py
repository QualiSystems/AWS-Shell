from unittest import TestCase

from cloudshell.cp.core.models import DeployApp
from mock import Mock, patch

from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContextModel
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
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
        cancellation_context = Mock()

        result = Mock()

        self.aws_shell.deploy_ami_operation.deploy = Mock(return_value=result)

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context
            deploy_app = DeployApp()
            deploy_app.actionParams = Mock()

            # act
            res = self.aws_shell.deploy_ami(self.command_context, [deploy_app], cancellation_context)


        self.assertEqual(res, result)
        self.aws_shell.deploy_ami_operation.deploy.assert_called_with(
                ec2_session=self.expected_shell_context.aws_api.ec2_session,
                s3_session=self.expected_shell_context.aws_api.s3_session,
                name=deploy_app.actionParams.appName,
                reservation=self.reservation_model,
                aws_ec2_cp_resource_model=self.expected_shell_context.aws_ec2_resource_model,
                ami_deploy_action=deploy_app,
                network_actions=[],
                ec2_client=self.expected_shell_context.aws_api.ec2_client,
                cancellation_context=cancellation_context,
                logger=self.expected_shell_context.logger)

    def test_cleanup_connectivity(self):
        # prepare
        req = '{"driverRequest": {"actions": [{"type": "cleanupNetwork", "actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356"}]}}'
        self.aws_shell.clean_up_operation.cleanup = Mock(return_value=True)
        actions_mock = Mock()
        result = None

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

                # act
            result = self.aws_shell.cleanup_connectivity(self.command_context, actions_mock)

        # assert
        self.aws_shell.clean_up_operation.cleanup.assert_called_with(
                ec2_client=self.expected_shell_context.aws_api.ec2_client,
                ec2_session=self.expected_shell_context.aws_api.ec2_session,
                s3_session=self.expected_shell_context.aws_api.s3_session,
                aws_ec2_data_model=self.expected_shell_context.aws_ec2_resource_model,
                reservation_id=self.command_context.reservation.reservation_id,
                actions=actions_mock,
                logger=self.expected_shell_context.logger)
        self.assertEquals(result, '{"driverResponse": {"actionResults": [true]}}')

    def test_prepare_connectivity(self):
        # Assert
        cancellation_context = Mock()
        req = '{"driverRequest": {"actions": [{"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356","actionTarget": null, "type": "prepareCloudInfra", "actionParams": {"type": "prepareCloudInfraParams", "cidr": "10.0.0.0/24"}}]}}'
        self.aws_shell.prepare_connectivity_operation.prepare_connectivity = Mock(return_value=True)
        res = None
        actions_mock = Mock()

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # Act
            res = self.aws_shell.prepare_connectivity(self.command_context, actions_mock, cancellation_context)

            # Assert
            self.aws_shell.prepare_connectivity_operation.prepare_connectivity.assert_called_with(
                    ec2_client=self.expected_shell_context.aws_api.ec2_client,
                    ec2_session=self.expected_shell_context.aws_api.ec2_session,
                    s3_session=self.expected_shell_context.aws_api.s3_session,
                    reservation=self.reservation_model,
                    aws_ec2_datamodel=self.expected_shell_context.aws_ec2_resource_model,
                    actions=actions_mock,
                    cancellation_context=cancellation_context,
                    logger=self.expected_shell_context.logger)
            self.assertEqual(res, True)

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

    def test_get_application_ports(self):
        remote_resource = Mock()
        remote_resource.fullname = 'my ami name'
        self.command_context.remote_endpoints = [remote_resource]

        deployed_model = Mock()
        deployed_model.vmdetails = Mock()
        deployed_model.vmdetails.vmCustomParams = Mock()
        self.aws_shell.model_parser.convert_app_resource_to_deployed_app = Mock(return_value=deployed_model)

        self.aws_shell.model_parser.try_get_deployed_connected_resource_instance_id = Mock(return_value='instance_id')
        self.aws_shell.deployed_app_ports_operation.get_app_ports_from_cloud_provider = Mock(return_value='bla')

        self.aws_shell.model_parser.get_allow_all_storage_traffic_from_connected_resource_details = Mock(return_value='True')

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            res = self.aws_shell.get_application_ports(self.command_context)

        assert res == 'bla'
        self.aws_shell.deployed_app_ports_operation.get_app_ports_from_cloud_provider.assert_called_with(
            ec2_session=self.expected_shell_context.aws_api.ec2_session,
            instance_id='instance_id',
            resource=remote_resource,
            allow_all_storage_traffic='True'
        )

    def test_get_access_key(self):
        self.command_context.remote_reservation = Mock()
        self.command_context.remote_reservation.reservation_id = 'reservation_id'
        self.aws_shell.access_key_operation.get_access_key = Mock(return_value='access_key')

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            res = self.aws_shell.get_access_key(self.command_context)

        assert res == 'access_key'
        self.aws_shell.access_key_operation.get_access_key(
                s3_session=self.expected_shell_context.aws_api.ec2_session,
                aws_ec2_resource_model=self.expected_shell_context.aws_ec2_resource_model,
                reservation_id=self.command_context.remote_reservation.reservation_id)

    def test_refresh_ip(self):
        self.aws_shell.model_parser.get_private_ip_from_connected_resource_details = Mock(return_value='private_ip')
        self.aws_shell.model_parser.get_public_ip_attr_from_connected_resource_details = Mock(return_value=('public_ip',
                                                                                                       "public_ip"))
        self.aws_shell.model_parser.try_get_deployed_connected_resource_instance_id = Mock(return_value='instance_id')
        self.aws_shell.model_parser.get_connectd_resource_fullname = Mock(return_value='resource_name')
        self.aws_shell.refresh_ip_operation.refresh_ip = Mock()

        with patch('cloudshell.cp.aws.aws_shell.AwsShellContext') as shell_context:
            shell_context.return_value = self.mock_context

            # act
            self.aws_shell.refresh_ip(self.command_context)

        self.aws_shell.refresh_ip_operation.refresh_ip(
            cloudshell_session=self.expected_shell_context.cloudshell_session,
            ec2_session=self.expected_shell_context.aws_api.ec2_session,
            deployed_instance_id='instance_id',
            private_ip_on_resource='private_ip',
            public_ip_on_resource='public_ip',
            resource_fullname='resource_name')

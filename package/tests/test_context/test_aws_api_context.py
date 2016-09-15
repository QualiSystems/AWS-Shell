from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.context.aws_api import AwsApiSessionContext


class TestAwsApiContext(TestCase):
    def test_aws_api_clients_proper_initialized(self):
        # Arrange
        aws_session_manager = Mock()
        expected_session = Mock()
        aws_session_manager.get_clients = Mock(return_value=expected_session)
        cloudshell_session = Mock()
        aws_ec2_resource_model = Mock()

        # Act
        with AwsApiSessionContext(aws_session_manager=aws_session_manager,
                                  cloudshell_session=cloudshell_session,
                                  aws_ec2_resource_model=aws_ec2_resource_model) as aws_api:

            aws_session_manager.get_clients.assert_called_with(cloudshell_session=cloudshell_session,
                                                                  aws_ec2_data_model=aws_ec2_resource_model)

            self.assertEquals(aws_api, expected_session)

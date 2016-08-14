from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.context.ec2_client import EC2ClientContext


class TestEC2ClientContext(TestCase):
    def test_aws_ec2_client_ontext_proper_initialized(self):
        # Arrange
        aws_session_manager = Mock()
        expected_client = Mock()
        aws_session_manager.get_ec2_client = Mock(return_value=expected_client)
        cloudshell_session = Mock()
        aws_ec2_resource_model = Mock()

        # Act
        with EC2ClientContext(aws_session_manager=aws_session_manager,
                              cloudshell_session=cloudshell_session,
                              aws_ec2_resource_model=aws_ec2_resource_model) as ec2_client:

            aws_session_manager.get_ec2_client.assert_called_with(cloudshell_session=cloudshell_session,
                                                                  aws_ec2_data_model=aws_ec2_resource_model)

            self.assertEquals(ec2_client, expected_client)

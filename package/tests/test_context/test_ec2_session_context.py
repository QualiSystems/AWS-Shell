from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.context.ec2_session import EC2SessionContext


class TestEC2SessionContext(TestCase):
    def test_aws_ec2_session_context_proper_initialized(self):
        # Arrange
        aws_session_manager = Mock()
        expected_session = Mock()
        aws_session_manager.get_ec2_session = Mock(return_value=expected_session)
        cloudshell_session = Mock()
        aws_ec2_resource_model = Mock()

        # Act
        with EC2SessionContext(aws_session_manager=aws_session_manager,
                               cloudshell_session=cloudshell_session,
                               aws_ec2_resource_model=aws_ec2_resource_model) as ec2_session:

            aws_session_manager.get_ec2_session.assert_called_with(cloudshell_session=cloudshell_session,
                                                                  aws_ec2_data_model=aws_ec2_resource_model)

            self.assertEquals(ec2_session, expected_session)

from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.context.s3_session import S3SessionContext


class TestS3SessionContext(TestCase):
    def test_aws_s3_session_context_proper_initialized(self):
        # Arrange
        aws_session_manager = Mock()
        expected_session = Mock()
        aws_session_manager.get_s3_session = Mock(return_value=expected_session)
        cloudshell_session = Mock()
        aws_ec2_resource_model = Mock()

        # Act
        with S3SessionContext(aws_session_manager=aws_session_manager,
                              cloudshell_session=cloudshell_session,
                              aws_ec2_resource_model=aws_ec2_resource_model) as s3_session:

            aws_session_manager.get_s3_session.assert_called_with(cloudshell_session=cloudshell_session,
                                                                   aws_ec2_data_model=aws_ec2_resource_model)

            self.assertEquals(s3_session, expected_session)

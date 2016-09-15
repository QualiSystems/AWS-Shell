from unittest import TestCase

import mock
from mock import Mock, patch, MagicMock

from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContext, AwsShellContextModel


class AwsAwsShellContext(TestCase):
    def test_aws_shell_context_proper_initialized(self):
        # Arrange
        aws_session_manager = Mock()
        command_context = Mock()
        with patch('cloudshell.cp.aws.domain.context.aws_shell.LoggingSessionContext') as logger:
            with mock.patch('cloudshell.cp.aws.domain.context.aws_shell.ErrorHandlingContext'):
                with mock.patch('cloudshell.cp.aws.domain.context.aws_shell.CloudShellSessionContext') as cloudshell_session:
                    with mock.patch('cloudshell.cp.aws.domain.context.aws_shell.AwsResourceModelContext') as aws_ec2_resource_model:
                        with mock.patch('cloudshell.cp.aws.domain.context.aws_shell.AwsApiSessionContext') as aws_api:
                            expected_context = AwsShellContextModel(logger=logger().__enter__(),
                                                                    cloudshell_session=cloudshell_session().__enter__(),
                                                                    aws_ec2_resource_model=aws_ec2_resource_model().__enter__(),
                                                                    aws_api=aws_api().__enter__())

                            # Act
                            with AwsShellContext(context=command_context,
                                                 aws_session_manager=aws_session_manager) as aws_shell_context:
                                # Assert
                                self.assertIsInstance(aws_shell_context, AwsShellContextModel)

                                self.assertEquals(aws_shell_context.logger, expected_context.logger)
                                self.assertEquals(aws_shell_context.cloudshell_session,
                                                  expected_context.cloudshell_session)
                                self.assertEquals(aws_shell_context.aws_ec2_resource_model,
                                                  expected_context.aws_ec2_resource_model)
                                self.assertEquals(aws_shell_context.aws_api, expected_context.aws_api)

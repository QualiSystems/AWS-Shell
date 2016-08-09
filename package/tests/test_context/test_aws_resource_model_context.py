from unittest import TestCase
from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.context.aws_resource_model import AwsResourceModelContext


class TestAwsResourceModelContext(TestCase):

    def test_aws_resource_model_context_proper_initialized(self):
        # Arrange
        context = Mock()
        context.resource = Mock()
        model_parser = Mock()
        expected_resource_model_context = MagicMock()
        model_parser.convert_to_aws_resource_model = Mock(return_value=expected_resource_model_context)

        with AwsResourceModelContext(context, model_parser) as aws_ec2_resource_model:

            model_parser.convert_to_aws_resource_model.assert_called_with(context.resource)
            self.assertEquals(aws_ec2_resource_model, expected_resource_model_context)



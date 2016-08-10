from unittest import TestCase
from mock import Mock
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider

DECRYPTED_PREFIX = "decrypted: "


def decrypt_mock(*args):
    value = args[0]
    result = Mock()
    result.Name = value
    result.Value = DECRYPTED_PREFIX + value
    return result


class TestAWSSessionProvider(TestCase):
    def setUp(self):
        self.session_provider = AWSSessionProvider()
        self.cloudshell_session = Mock()
        self.cloudshell_session.DecryptPassword = Mock(side_effect=decrypt_mock)

        self.aws_ec2_data_model = Mock()
        self.aws_ec2_data_model.aws_access_key_id = "access key"
        self.aws_ec2_data_model.aws_secret_access_key = "secret key"
        self.aws_ec2_data_model.region = "region"


    def test_get_clients(self):

        aws_api = self.session_provider.get_clients(cloudshell_session=self.cloudshell_session,
                                                    aws_ec2_data_model=self.aws_ec2_data_model)
        self.assertIsNotNone(aws_api.ec2_session)
        self.assertIsNotNone(aws_api.ec2_client)
        self.assertIsNotNone(aws_api.s3_session)

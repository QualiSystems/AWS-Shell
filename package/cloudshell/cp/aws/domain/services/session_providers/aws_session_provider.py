import ConfigParser
import os

import boto3


class AWSSessionProvider(object):
    EC2 = 'ec2'

    def __init__(self):
        self.test_cred_path = os.path.join(os.path.dirname(__file__), 'test_cred.ini')
        if not os.path.isfile(self.test_cred_path):
            self.test_cred_path = ''

    def get_ec2_session(self, cloudshell_session, aws_ec2_data_model):
        credentials = self._get_aws_credentials(cloudshell_session, aws_ec2_data_model)
        aws_session = self._get_aws_session(aws_ec2_data_model, credentials)

        if not aws_session:
            raise ValueError('Could not create AWS Session')
        return aws_session.resource(self.EC2)

    @staticmethod
    def _get_aws_session(aws_ec2_data_model, credentials):
        if not credentials:
            aws_session = boto3.Session(region_name=aws_ec2_data_model.region)
        else:
            aws_session = boto3.Session(
                aws_access_key_id=credentials.access_key_id,
                aws_secret_access_key=credentials.secret_access_key,
                region_name=aws_ec2_data_model.region)
        return aws_session

    def _get_aws_credentials(self, cloudshell_session=None, aws_ec2_data_model=None):
        if self.test_cred_path:
            return self._get_test_credentials()
        if cloudshell_session and aws_ec2_data_model.aws_access_key_id and aws_ec2_data_model.aws_secret_access_key:
            return AWSCredentials(
                self._decrypt_key(cloudshell_session, aws_ec2_data_model.aws_access_key_id),
                self._decrypt_key(cloudshell_session, aws_ec2_data_model.aws_secret_access_key))
        return None

    def _get_test_credentials(self):
        config = ConfigParser.ConfigParser()
        config_path = self.test_cred_path
        config.readfp(open(config_path))
        return AWSCredentials(config.get('Credentials', 'Access Key ID'),
                              config.get('Credentials', 'Secret Access Key'))

    @staticmethod
    def _decrypt_key(cloudshell_session, field):
        return cloudshell_session.DecryptPassword(field).Value


class AWSCredentials(object):
    def __init__(self, key_id, access_key):
        self.access_key_id = key_id
        self.secret_access_key = access_key

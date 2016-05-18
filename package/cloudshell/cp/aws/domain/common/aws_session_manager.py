import ConfigParser
import os


class AWSSessionManager(object):
    def __init__(self):
        self.test_cred_path = os.path.join(os.path.dirname(__file__), 'test_cred.ini')
        if not os.path.isfile(self.test_cred_path):
            self.test_cred_path = ''

    def get_credentials(self):
        if self.test_cred_path:
            return self._get_test_credentials()

    def _get_test_credentials(self):
        config = ConfigParser.ConfigParser()
        config_path = self.test_cred_path
        config.readfp(open(config_path))
        return config.get('Credentials', 'Access Key ID'),config.get('Credentials', 'Secret Access Key')

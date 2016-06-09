import os


class KeyPairProvider(object):
    # S3 = 's3'
    FILE_SYSTEM = 'file_system'
    SUPPORTED_LOCATIONS = [
        # S3,
        FILE_SYSTEM]
    LOAD_FILE_FUNCTION_PREFIX = 'load_from_{0}'

    def load(self, path, key_name, location_type):
        if location_type not in self.SUPPORTED_LOCATIONS:
            raise ValueError('Unsupported Key Location: {0}'.format(location_type))
        if not path:
            raise ValueError('The path to the key cannot be empty')
        if not key_name:
            raise ValueError('The key name cannot be empty')

        loader_function = getattr(self, self.LOAD_FILE_FUNCTION_PREFIX.format(location_type))
        return loader_function(path, key_name)

    @staticmethod
    def load_from_file_system(path, name):
        name_ext = '{0}.pem'.format(name)
        location = os.path.join(path, name_ext)
        with open(location) as key_file:
            return key_file.readlines()

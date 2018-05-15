from jsonpickle import json


class DeployNetworkingResultModel(object):
    def __init__(self, action_id):
        self.action_id = action_id  # type: str
        self.interface_id = ''  # type: str
        self.device_index = None  # type: int
        self.private_ip = ''  # type: str
        self.public_ip = ''  # type: str
        self.mac_address = ''  # type: str
        self.is_elastic_ip = False  # type: bool


class SetAppSecurityGroupActionResult(object):
    def __init__(self):
        self.appName = ''
        self.success = True
        self.error = ''

    def convert_to_json(self):
        result = {'appName': self.appName, 'error': self.error, 'success': self.success}
        return json.dumps(result)

    @staticmethod
    def to_json(results):
        if not results:
            return

        return json.dumps([r.__dict__ for r in results])


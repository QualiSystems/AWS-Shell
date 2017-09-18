from jsonpickle import json


class CancellationException(Exception):
    """Raised when command was cancelled from the CloudShell"""

    def __init__(self, message, data):
        """
        :param str message:
        :param dict data:
        :return:
        """
        # Call the base class constructor with the parameters it needs
        super(CancellationException, self).__init__(message)

        self.data = data if data else {}


class SetAppSecurityGroupException(Exception):
    def __init__(self, data):
        """
        :param list[SetAppSecurityGroupActionResult] data:
        """
        self.jsonResult = self._to_json(data)
        super(SetAppSecurityGroupException, self).__init__(self.jsonResult)

    @staticmethod
    def _to_json(data):
        result = [{'appName': actionResult.appName, 'error': actionResult.errorMessage.message} for actionResult in data]
        return json.dumps(result)

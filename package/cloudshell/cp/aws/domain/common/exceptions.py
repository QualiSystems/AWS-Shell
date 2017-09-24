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
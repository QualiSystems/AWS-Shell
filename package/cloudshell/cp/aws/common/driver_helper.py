from cloudshell.api.cloudshell_api import CloudShellAPISession


class CloudshellDriverHelper(object):
    def __init__(self):
        self.session_class = CloudShellAPISession

    def get_session(self, server_address, token, reservation_domain):
        """
        gets the current session

        :param str reservation_domain: reservation domain
        :param token: the admin authentication token
        :param server_address: cloudshell server address
        :return CloudShellAPISession
        """
        return self.session_class(host=server_address,
                                  token_id=token,
                                  username=None,
                                  password=None,
                                  domain=reservation_domain)
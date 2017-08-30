
class ConnectivityActionResult(object):
    def __init__(self):
        self.actionId = ''
        self.success = True
        self.infoMessage = ''
        self.errorMessage = ''


class PrepareNetworkActionResult(ConnectivityActionResult):
    def __init__(self):
        ConnectivityActionResult.__init__(self)
        self.vpcId = ''
        self.securityGroupId = ''
        self.type = 'PrepareNetwork'

class ConnectionParamsBase(object):
    def __init__(self):
        self.cidr = ''  # type: str
        self.subnetServiceAttributes = []  # type: list[NetworkActionAttribute]


class SubnetConnectionParams(ConnectionParamsBase):
    def __init__(self):
        ConnectionParamsBase.__init__(self)
        self.subnet_id = ''

    def is_public_subnet(self):
        for attr in self.subnetServiceAttributes:
            if attr.name == "Public":
                return True if attr.value.lower() == "true" else False
        return True  # default public subnet value is True


class PreapreSubnetParams(ConnectionParamsBase):
    def __init__(self):
        ConnectionParamsBase.__init__(self)
        self.is_public = False  # type: bool


class PrepareNetworkParams(ConnectionParamsBase):
    def __init__(self):
        ConnectionParamsBase.__init__(self)
        del self.subnetServiceAttributes


class NetworkActionAttribute(object):
    def __init__(self):
        self.name = ''
        self.value = ''


class NetworkAction(object):
    def __init__(self):
        self.id = ''  # type: str
        self.type = ''  # type: str
        self.connection_params = None  # type: ConnectionParamsBase
        self.custom_attributes = []  # type: [NetworkActionAttribute]


class DeployNetworkingResultModel(object):
    def __init__(self, action_id):
        self.action_id = action_id  # type: str
        self.interface_id = ''  # type: str
        self.device_index = None  # type: int
        self.private_ip = ''  # type: str
        self.public_ip = ''  # type: str
        self.mac_address = ''  # type: str


class DeployNetworkingResultDto(object):
    def __init__(self, action_id, success, interface_data, info='', error=''):
        self.actionId = action_id  # type: str
        self.type = 'connectToSubnet'
        self.success = success
        self.interface = interface_data
        self.infoMessage = info,
        self.errorMessage = error

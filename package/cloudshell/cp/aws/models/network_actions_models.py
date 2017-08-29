class ConnectionParamsBase(object):
    def __init__(self):
        self.cidr = ''  # type: str
        self.subnetServiceAttributes = []  # type: [NetworkActionAttribute]


class SubnetConnectionParams(ConnectionParamsBase):
    def __init__(self):
        ConnectionParamsBase.__init__(self)
        self.subnet_id = ''


class PrepareSubnetParams(ConnectionParamsBase):
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

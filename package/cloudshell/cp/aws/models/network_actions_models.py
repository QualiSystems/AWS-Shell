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


class PrepareSubnetParams(ConnectionParamsBase):
    def __init__(self, cidr=None, alias='', is_public=True):
        """
        :param str cidr:
        :param str alias:
        :param bool is_public:
        """
        ConnectionParamsBase.__init__(self)
        self.cidr = cidr
        self.is_public = is_public
        self.alias = alias


class PrepareNetworkParams(ConnectionParamsBase):
    def __init__(self):
        ConnectionParamsBase.__init__(self)
        del self.subnetServiceAttributes


class NetworkActionAttribute(object):
    def __init__(self):
        self.name = ''
        self.value = ''


class NetworkAction(object):
    def __init__(self, id=None, type=None, connection_params=None, custom_attributes=None):
        """
        :param str id:
        :param str type:
        :param ConnectionParamsBase connection_params:
        :param [NetworkActionAttribute] custom_attributes:
        """
        self.id = id or ''
        self.type = type or ''
        self.connection_params = connection_params
        self.custom_attributes = custom_attributes or []


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
        self.infoMessage = info
        self.errorMessage = error

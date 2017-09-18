from jsonpickle import json

VNIC_NAME_ATTRIBUTE = "Vnic Name"


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

    @property
    def device_index(self):
        for attr in self.subnetServiceAttributes:
            if attr.name == VNIC_NAME_ATTRIBUTE:
                return int(attr.value)
        return None

    @device_index.setter
    def device_index(self, value):
        for attr in self.subnetServiceAttributes:
            if attr.name == VNIC_NAME_ATTRIBUTE:
                attr.value = int(value)
                return

        vnic_name_attr = NetworkActionAttribute()
        vnic_name_attr.name = VNIC_NAME_ATTRIBUTE
        vnic_name_attr.value = int(value)
        self.subnetServiceAttributes.append(vnic_name_attr)


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


class PrepareSubnetActionResult(ConnectivityActionResult):
    def __init__(self):
        ConnectivityActionResult.__init__(self)
        self.subnetId = ''


class ConnectToSubnetActionResult(ConnectivityActionResult):
    def __init__(self, action_id, success, interface_data, info='', error=''):
        ConnectivityActionResult.__init__(self)
        self.actionId = action_id  # type: str
        self.type = 'connectToSubnet'
        self.success = success
        self.interface = interface_data
        self.infoMessage = info
        self.errorMessage = error


class SetAppSecurityGroupActionResult(object):
    def __init__(self):
        self.appName = ''
        self.success = True
        self.errorMessage = ''

    def to_json(self):
        result = {'appName': self.appName, 'error': self.errorMessage, 'success': self.success}
        return json.dumps(result)

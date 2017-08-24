from cloudshell.cp.aws.common.converters import convert_to_bool
from cloudshell.cp.aws.models.network_actions_models import *


class ConnectionParamsParser(object):
    def __init__(self):
        pass

    @staticmethod
    def parse(params_data):
        """
        :param dict params_data:
        :rtype: ConnectionParamsBase
        """
        params_type = params_data["type"]
        params = None

        if params_type == "connectToSubnetParams":
            params = SubnetConnectionParams()
            params.subnet_id = params_data['subnetId']

        elif params_type == "prepareSubnetParams":
            params = PreapreSubnetParams()
            params.is_public = convert_to_bool(params_data['isPublic'])

        elif params_type == "prepareNetworkParams":
            params = PrepareNetworkParams()

        else:
            raise ValueError("Unsupported connection params type {0}".format(type))

        ConnectionParamsParser.parse_base_data(params, params_data)

        return params

    @staticmethod
    def parse_base_data(params_base, data):
        """
        :param ConnectionParamsBase params_base:
        :param dict data:
        :return:
        """
        params_base.cidr = data['cidr']
        params_base.subnetServiceAttributes = ConnectionParamsParser.parse_subnet_service_attributes(data)

    @staticmethod
    def parse_subnet_service_attributes(data):
        """
        :param dict data:
        :rtype: [NetworkActionAttribute]
        """

        if "subnetServiceAttributes" not in data:
            return None

        result = []

        for raw_action_attribute in data["subnetServiceAttributes"]:
            if raw_action_attribute["type"] == "subnetServiceAttribute":
                attribute_obj = NetworkActionAttribute()
                attribute_obj.name = raw_action_attribute["attributeName"]
                attribute_obj.value = raw_action_attribute["attributeValue"]
                result.append(attribute_obj)

        return result
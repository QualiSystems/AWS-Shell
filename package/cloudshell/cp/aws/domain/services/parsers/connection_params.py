from cloudshell.cp.aws.common.converters import convert_to_bool
from cloudshell.cp.aws.models.network_actions_models import SubnetActionParams
from cloudshell.cp.aws.models.network_actions_models import NetworkActionAttribute
from cloudshell.cp.core.models import PrepareCloudInfraParams
from cloudshell.cp.core.models import PrepareSubnetParams
class ActionParamsParser(object):
    def __init__(self):
        pass

    @staticmethod
    def parse(action):
        """
        :param dict params_data:
        :rtype: ActionParamsBase
        """
        params_data = action.get("actionParams")
        params = None
        if not params_data:
            return params

        params_type = params_data["type"]

        if params_type == "connectToSubnetParams":
            params = SubnetActionParams()
            params.subnet_id = params_data['subnetId']

        elif params_type == "prepareSubnetParams":
            params = PrepareSubnetParams()
            params.is_public = convert_to_bool(params_data['isPublic'])
            params.alias = params_data.get('alias', '')

        elif params_type == "prepareCloudInfraParams":
            params = PrepareCloudInfraParams()

        else:
            raise ValueError("Unsupported connection params type {0}".format(type))

        ActionParamsParser.parse_base_data(params, params_data, action)

        return params

    @staticmethod
    def parse_base_data(params_base, data, action):
        """
        :param ActionParamsBase params_base:
        :param dict data:
        :param dict action:
        :return:
        """
        params_base.cidr = data['cidr']
        params_base.subnetServiceAttributes = ActionParamsParser.parse_subnet_service_attributes(data)
        params_base.custom_attributes = ActionParamsParser.parse_custom_network_action_attributes(action)

    @staticmethod
    def parse_custom_network_action_attributes(action):
        """
        :param dict action:
        :rtype: [NetworkActionAttribute]
        """
        result = []
        if not isinstance(action.get("customActionAttributes"), list):
            return result

        for raw_action_attribute in action["customActionAttributes"]:
            attribute_obj = NetworkActionAttribute()
            attribute_obj.name = raw_action_attribute["attributeName"]
            attribute_obj.value = raw_action_attribute["attributeValue"]
            result.append(attribute_obj)

        return result

    @staticmethod
    def parse_subnet_service_attributes(data):
        """
        :param dict data:
        :rtype: [NetworkActionAttribute]
        """
        result = []

        if not isinstance(data.get("subnetServiceAttributes"), list):
            return result

        for raw_action_attribute in data["subnetServiceAttributes"]:
            if raw_action_attribute["type"] == "subnetServiceAttribute":
                attribute_obj = NetworkActionAttribute()
                attribute_obj.name = raw_action_attribute["attributeName"]
                attribute_obj.value = raw_action_attribute["attributeValue"]
                result.append(attribute_obj)
        return result
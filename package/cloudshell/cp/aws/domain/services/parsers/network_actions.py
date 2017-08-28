from cloudshell.cp.aws.domain.services.parsers.connection_params import ConnectionParamsParser
from cloudshell.cp.aws.models.network_actions_models import NetworkAction, NetworkActionAttribute


class NetworkActionsParser(object):
    def __init__(self):
        pass

    @staticmethod
    def parse_network_actions_data(actions_data):
        """
        :param [dict] actions_data:
        """
        if not isinstance(actions_data, list):
            return None

        parsed_data = []

        for action in actions_data:
            network_action = NetworkAction()
            network_action.id = action["actionId"]
            network_action.type = action["type"]
            network_action.custom_attributes = NetworkActionsParser.parse_custom_network_action_attributes(action)
            network_action.connection_params = ConnectionParamsParser.parse(action["connectionParams"])
            parsed_data.append(network_action)

        return parsed_data if(len(parsed_data) > 0) else None

    @staticmethod
    def parse_custom_network_action_attributes(action):
        """
        :param dict action:
        :rtype: [NetworkActionAttribute]
        """
        result = []

        for raw_action_attribute in action["customActionAttributes"]:
            attribute_obj = NetworkActionAttribute()
            attribute_obj.name = raw_action_attribute["Name"]
            attribute_obj.value = raw_action_attribute["Value"]
            result.append(attribute_obj)

        return result

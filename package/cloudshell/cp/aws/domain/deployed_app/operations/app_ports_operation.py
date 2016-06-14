from cloudshell.cp.aws.domain.services.model_parser.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.port_data import PortData


class DeployedAppPortsOperation(object):
    def __init__(self):
        pass

    def get_formated_deployed_app_ports(self, custom_params):
        """
        :param custom_params:
        :return:
        """
        inbound_ports_value = self._get_custom_param_value(custom_params, "inbound_ports")
        outbound_ports_value = self._get_custom_param_value(custom_params, "outbound_ports")

        if not inbound_ports_value and not outbound_ports_value:
            return ""

        result_str_list = []

        if inbound_ports_value:
            inbound_ports = PortGroupAttributeParser.parse_port_group_attribute(inbound_ports_value)
            if inbound_ports:
                result_str_list.append("Inbound ports:")
                for rule in inbound_ports:
                    result_str_list.append(self._port_rule_to_string(rule))
                result_str_list.append('')

        if outbound_ports_value:
            outbound_ports = PortGroupAttributeParser.parse_port_group_attribute(outbound_ports_value)
            if outbound_ports:
                result_str_list.append("Outbound ports:")
                for rule in outbound_ports:
                    result_str_list.append(self._port_rule_to_string(rule))

        return '\n'.join(result_str_list).strip()

    def _get_custom_param_value(self, custom_params, name):
        name = name.lower()
        params = filter(lambda x: x.name.lower() == name, custom_params)
        if len(params) == 1:
            return params[0].value
        return False

    def _port_rule_to_string(self, port_rule):
        """
        :param PortData port_rule:
        :return:
        """
        if port_rule.from_port == port_rule.to_port:
            port_str = port_rule.from_port
            port_postfix = ""
        else:
            port_str = "{0}-{1}".format(port_rule.from_port, port_rule.to_port)
            port_postfix = "s"

        return "Port{0} {1} {2}".format(port_postfix, port_str, port_rule.protocol)

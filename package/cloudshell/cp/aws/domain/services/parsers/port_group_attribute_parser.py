import re

import ipaddress

from cloudshell.cp.aws.models.port_data import PortData


class PortGroupAttributeParser(object):
    PORT_DATA_MATCH = re.compile(r"^(?P<from_port>\d+)"
                                 r"(-(?P<to_port>\d+))?"
                                 r"(:(?P<protocol>(udp|tcp|icmp)))?"
                                 r"(:(?P<destination>\S+))?$", re.IGNORECASE)

    @staticmethod
    def parse_security_group_rules_to_port_data(rules):
        """
        :param [list] rules:
        :return:
        :rtype: list[PortData]
        """
        if not isinstance(rules, list):
            return None

        parsed_data = []

        for rule in rules:
            port_data = PortData(rule.fromPort, rule.toPort, rule.protocol, rule.source)
            parsed_data.append(port_data)

        return parsed_data if (len(parsed_data) > 0) else None

    @staticmethod
    def parse_port_group_attribute(ports_attribute):
        """
        :param ports_attribute:
        :return:
        :rtype: list[PortData]
        """
        if ports_attribute:
            splitted_ports = filter(lambda x: x, ports_attribute.strip().split(';'))
            port_data_array = [PortGroupAttributeParser._single_port_parse(port.strip()) for port in splitted_ports]
            return port_data_array
        return None

    @staticmethod
    def _single_port_parse(ports_attribute):
        destination = "0.0.0.0/0"
        protocol = "tcp"

        from_to_protocol_match = PortGroupAttributeParser.PORT_DATA_MATCH.search(ports_attribute)
        if from_to_protocol_match:
            port_data_params = from_to_protocol_match.groupdict()
            if not port_data_params.get("to_port"):
                port_data_params["to_port"] = port_data_params.get("from_port")
            if not port_data_params.get("destination"):
                port_data_params["destination"] = destination
            if not port_data_params.get("protocol"):
                port_data_params["protocol"] = protocol
            return PortData(**port_data_params)

        raise ValueError("The value '{0}' is not a valid ports rule".format(ports_attribute))

    @staticmethod
    def _is_valid_source(source):
        try:
            # check if source is a valid CIDR
            ipaddress.ip_network(unicode(source))
        except:
            return False

        return True

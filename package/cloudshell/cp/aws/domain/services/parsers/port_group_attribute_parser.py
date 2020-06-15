import re

import ipaddress

from cloudshell.cp.aws.models.port_data import PortData


class PortGroupAttributeParser(object):

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
        from_port = 'from_port'
        to_port = 'to_port'
        protocol = 'protocol'
        tcp = 'tcp'

        # # 4000-5000:tcp:10.0.0.20 or 4000-5000:tcp:10.0.0.0/24
        # regex_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+):(?P<protocol>(udp|tcp)):(?P<source>.+))$",
        #                        ports_attribute,
        #                        flags=re.IGNORECASE)
        # if regex_match:
        #     from_port = regex_match.group(from_port)
        #     to_port = regex_match.group(to_port)
        #     protocol = regex_match.group(protocol).lower()
        #     req_source = regex_match.group(source)
        #     if PortGroupAttributeParser._is_valid_source(req_source):
        #         return PortData(from_port, to_port, protocol, req_source)
        #
        # # 4000:tcp:10.0.0.20 or 4000:tcp:10.0.0.0/24
        # regex_match = re.match(r"^((?P<from_port>\d+):(?P<protocol>(udp|tcp)):(?P<source>.+))$",
        #                        ports_attribute,
        #                        flags=re.IGNORECASE)
        # if regex_match:
        #     from_port = regex_match.group(from_port)
        #     to_port = from_port
        #     protocol = regex_match.group(protocol).lower()
        #     req_source = regex_match.group(source)
        #     if PortGroupAttributeParser._is_valid_source(req_source):
        #         return PortData(from_port, to_port, protocol, req_source)
        #
        # # 80-50000:udp
        # regex_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+):(?P<protocol>(udp|tcp)))$",
        #                        ports_attribute,
        #                        flags=re.IGNORECASE)
        # if regex_match:
        #     from_port = regex_match.group(from_port)
        #     to_port = regex_match.group(to_port)
        #     protocol = regex_match.group(protocol).lower()
        #     return PortData(from_port, to_port, protocol, default_source)

        from_to_protocol_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+):(?P<protocol>(udp|tcp)))$",
                                          ports_attribute,
                                          flags=re.IGNORECASE)

        # 80-50000:udp
        if from_to_protocol_match:
            from_port = from_to_protocol_match.group(from_port)
            to_port = from_to_protocol_match.group(to_port)
            protocol = from_to_protocol_match.group(protocol).lower()
            return PortData(from_port, to_port, protocol, destination)

        from_protocol_match = re.match(r"^((?P<from_port>\d+):(?P<protocol>(udp|tcp)))$",
                                       ports_attribute,
                                       flags=re.IGNORECASE)

        # 80:udp
        if from_protocol_match:
            from_port = from_protocol_match.group(from_port)
            to_port = from_port
            protocol = from_protocol_match.group(protocol).lower()
            return PortData(from_port, to_port, protocol, destination)

        from_to_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+))$", ports_attribute)

        # 20-80

        if from_to_match:
            from_port = from_to_match.group(from_port)
            to_port = from_to_match.group(to_port)
            protocol = tcp
            return PortData(from_port, to_port, protocol, destination)

        port_match = re.match(r"^((?P<from_port>\d+))$", ports_attribute)
        # 80
        if port_match:
            from_port = port_match.group(from_port)
            to_port = from_port
            protocol = tcp
            return PortData(from_port, to_port, protocol, destination)

        raise ValueError("The value '{0}' is not a valid ports rule".format(ports_attribute))

    @staticmethod
    def _is_valid_source(source):
        try:
            # check if source is a valid CIDR
            ipaddress.ip_network(unicode(source))
        except:
            return False

        return True

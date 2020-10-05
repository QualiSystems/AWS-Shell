from collections import defaultdict

import re
from cloudshell.shell.core.driver_context import ResourceContextDetails
from jsonpickle import json

from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.parsers.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.port_data import PortData
from cloudshell.cp.aws.domain.services.parsers.custom_param_extractor import VmCustomParamsExtractor


class DeployedAppPortsOperation(object):
    def __init__(self, vm_custom_params_extractor, security_group_service, instance_service):
        """
        :param VmCustomParamsExtractor vm_custom_params_extractor:
        :param security_group_service:
        :type security_group_service: cloudshell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :return:
        """
        self.vm_custom_params_extractor = vm_custom_params_extractor
        self.security_group_service = security_group_service
        self.instance_service = instance_service

    def get_formated_deployed_app_ports(self, custom_params):
        """
        :param custom_params:
        :return:
        """
        inbound_ports_value = self.vm_custom_params_extractor.get_custom_param_value(custom_params, "inbound_ports")
        outbound_ports_value = self.vm_custom_params_extractor.get_custom_param_value(custom_params, "outbound_ports")

        if not inbound_ports_value and not outbound_ports_value:
            return "No ports are open for inbound and outbound traffic outside of the Sandbox"

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

    def get_app_ports_from_cloud_provider(self, ec2_session, instance_id, resource, allow_all_storage_traffic):
        """
        :param ec2_session: EC2 session
        :param string instance_id:
        :param ResourceContextDetails resource:
        :param string allow_all_storage_traffic:
        """
        instance = self.instance_service.get_active_instance_by_id(ec2_session, instance_id)
        network_interfaces = instance.network_interfaces

        result_str_list = ['App Name: ' + resource.fullname,
                           'Allow Sandbox Traffic: ' + str(allow_all_storage_traffic)]

        # group network interfaces by subnet into dictionary
        network_interfaces_dict = defaultdict(list)
        for network_interface in network_interfaces:
            network_interfaces_dict[network_interface.subnet_id].append(network_interface)

        for key, value in network_interfaces_dict.iteritems():
            for network_interface in value:
                subnet_name = self._get_network_interface_subnet_name(network_interface)
                result_str_list.append('Subnet Id: ' + key)
                result_str_list.append('Subnet Name: ' + subnet_name)

                # get security groups for network interface
                custom_security_group = self.security_group_service.get_custom_security_group(
                    ec2_session=ec2_session,
                    network_interface=network_interface)

                inbound_ports_security_group = self.security_group_service.get_inbound_ports_security_group(
                    ec2_session=ec2_session,
                    network_interface=network_interface)

                security_groups = []
                if custom_security_group:
                    security_groups.append(custom_security_group)
                if inbound_ports_security_group:
                    security_groups.append(inbound_ports_security_group)

                # convert ip permissions of security groups to string
                for security_group in security_groups:
                    ip_permissions_string = self._ip_permissions_to_string(security_group.ip_permissions)
                    if ip_permissions_string:
                        result_str_list.append(ip_permissions_string)

        return '\n'.join(result_str_list).strip()

    def _get_network_interface_subnet_name(self, network_interface):
        if network_interface.subnet.tags:
            subnet_tags = {d["Key"]: d["Value"] for d in network_interface.subnet.tags}
            subnet_full_name = AWSModelsParser.get_attribute_value_by_name_ignoring_namespace(subnet_tags, 'Name')
            reservation_id = AWSModelsParser.get_attribute_value_by_name_ignoring_namespace(subnet_tags,
                                                                                            'ReservationId')
            remove_from_subnet_name = "Reservation: {}".format(reservation_id)
            return re.sub(remove_from_subnet_name, '', subnet_full_name).strip()
        return ""

    def _ip_permissions_to_string(self, ip_permissions):
        if not isinstance(ip_permissions, list):
            return None

        result = []

        for ip_permission in ip_permissions:
            if ip_permission['FromPort'] == ip_permission['ToPort']:
                port_str = ip_permission['FromPort']
                port_postfix = ""
            else:
                port_str = "{0}-{1}".format(ip_permission['FromPort'], ip_permission['ToPort'])
                port_postfix = "s"

            result.append("Port{0}: {1}, Protocol: {2}, Source: {3}".format(port_postfix, port_str,
                                                                            ip_permission['IpProtocol'],
                                                                            self._convert_ip_ranges_to_string(
                                                                                ip_permission['IpRanges'])))
        return '\n'.join(result).strip()

    def _convert_ip_ranges_to_string(self, ip_ranges):
        if not isinstance(ip_ranges, list):
            return None

        cidrs = []

        for ip_range in ip_ranges:
            if not isinstance(ip_range, dict):
                continue
            cidr = ip_range.get('CidrIp')
            if cidr:
                cidrs.append(cidr)

        return ', '.join(cidrs)

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

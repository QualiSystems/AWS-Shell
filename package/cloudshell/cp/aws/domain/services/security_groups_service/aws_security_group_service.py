import re
import uuid

from cloudshell.cp.aws.models.port_data import PortData
from cloudshell.cp.aws.device_access_layer.aws_api import AWSApi


class AWSSecurityGroupService(object):

    QUALI_SECURITY_GROUP = "Quali_security_group"
    QUALI_SECURITY_GROUP_DESCRIPTION = "Quali Security Group"

    def __init__(self, aws_api):
        """

        :param AWSApi aws_api:
        :return:
        """
        self.aws_api = aws_api

    def create_security_group(self, ami_deployment_model, aws_ec2_cp_resource_model, ec2_session):

        inbound_ports = self._parse_port_group_attribute(ami_deployment_model.inbound_ports)
        outbound_ports = self._parse_port_group_attribute(ami_deployment_model.outbound_ports)
        security_group_id = None

        # if the deployment model contains inbound / outbound ports
        if inbound_ports or outbound_ports:
            # create a new security port group based on the attributes
            # in the end creates a tag "CreatedBy : Quali"
            security_group = self._create_security_group_with_port_group(ec2_session,
                                                                         inbound_ports,
                                                                         outbound_ports,
                                                                         aws_ec2_cp_resource_model.vpc)
            security_group_id = security_group.group_id

        return security_group_id

    def _create_security_group_with_port_group(self, ec2_session, inbound_ports, outbound_ports, vpc):

        security_group_name = AWSSecurityGroupService.QUALI_SECURITY_GROUP + " " + str(uuid.uuid4())

        # creating the security group
        security_group = self.aws_api.create_security_group(ec2_session,
                                                            security_group_name,
                                                            AWSSecurityGroupService.QUALI_SECURITY_GROUP_DESCRIPTION,
                                                            vpc)
        # adding inbound port rules
        if inbound_ports:
            ip_permissions = [self._get_ip_permission_object(port) for port in inbound_ports if port is not None]
            security_group.authorize_ingress(IpPermissions=ip_permissions)

        if outbound_ports:
            ip_permissions = [self._get_ip_permission_object(port) for port in outbound_ports if port is not None]
            security_group.authorize_egress(IpPermissions=ip_permissions)

        # setting tags on the created security group
        self.aws_api.set_security_group_tags(security_group, security_group_name)

        return security_group

    @staticmethod
    def _parse_port_group_attribute(ports_attribute):

        if ports_attribute:
            splitted_ports = ports_attribute.split(';')
            port_data_array = [AWSSecurityGroupService._single_port_parse(port) for port in splitted_ports]
            return port_data_array
        return None

    @staticmethod
    def _single_port_parse(ports_attribute):
        destination = "0.0.0.0/0"
        from_port = 'from_port'
        to_port = 'to_port'
        protocol = 'protocol'
        tcp = 'tcp'

        port_data = None

        from_to_protocol_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+):(?P<protocol>(udp|tcp)))$",
                                          ports_attribute)

        # 80-50000:udp
        if from_to_protocol_match:
            from_port = from_to_protocol_match.group(from_port)
            to_port = from_to_protocol_match.group(to_port)
            protocol = from_to_protocol_match.group(protocol)
            return PortData(from_port, to_port, protocol, destination)

        from_protocol_match = re.match(r"^((?P<from_port>\d+):(?P<protocol>(udp|tcp)))$", ports_attribute)

        # 80:udp
        if from_protocol_match:
            from_port = from_protocol_match.group(from_port)
            to_port = from_port
            protocol = from_protocol_match.group(protocol)
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

        return port_data

    @staticmethod
    def _get_ip_permission_object(port_data):
        return {
            'IpProtocol': port_data.protocol,
            'FromPort': int(port_data.from_port),
            'ToPort': int(port_data.to_port),
            'IpRanges': [
                {
                    'CidrIp': port_data.destination
                }
            ]}

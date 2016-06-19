from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.security_group import AWSSecurityGroupService
from cloudshell.cp.aws.domain.services.model_parser.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.port_data import PortData


class TestSecurityGroups(TestCase):
    def setUp(self):
        self.port_data = PortData('1', '2', 'tcp', '0.0.0.0/0')

    def test_get_ip_permission_object(self):
        permission_object = AWSSecurityGroupService.get_ip_permission_object(self.port_data)
        self.assertEquals(str(permission_object['FromPort']), self.port_data.from_port)
        self.assertEquals(str(permission_object['ToPort']), self.port_data.to_port)
        self.assertEquals(permission_object['IpRanges'][0]['CidrIp'], self.port_data.destination)
        self.assertEquals(permission_object['IpProtocol'], self.port_data.protocol)

    def test_port_group_parser(self):
        ports_attribute = " 1-3:tcp; 1:udp; 1-3;1;  "
        ports = PortGroupAttributeParser.parse_port_group_attribute(ports_attribute)

        self.assertEquals(ports[0].from_port, '1')
        self.assertEquals(ports[0].to_port, '3')
        self.assertEquals(ports[0].protocol, 'tcp')

        self.assertEquals(ports[1].from_port, '1')
        self.assertEquals(ports[1].to_port, '1')
        self.assertEquals(ports[1].protocol, 'udp')

        self.assertEquals(ports[2].from_port, '1')
        self.assertEquals(ports[2].to_port, '3')
        self.assertEquals(ports[2].protocol, "tcp")

        self.assertEquals(ports[3].from_port, '1')
        self.assertEquals(ports[3].to_port, '1')
        self.assertEquals(ports[3].protocol, 'tcp')

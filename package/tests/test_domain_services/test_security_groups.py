from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.parsers.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.port_data import PortData


class TestSecurityGroups(TestCase):
    def setUp(self):
        self.port_data = PortData('1', '2', 'tcp', '0.0.0.0/0')
        self.tag_service = Mock()
        self.sg_service = SecurityGroupService(self.tag_service)

    def test_get_ip_permission_object(self):
        permission_object = SecurityGroupService.get_ip_permission_object(self.port_data)
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

    def test_delete_sg(self):
        sg = Mock()
        self.sg_service.delete_security_group(sg)

        self.assertTrue(sg.delete.called)

    def test_delete_sg_exception(self):
        sg = Mock()
        sg.delete = Mock(side_effect=Exception())
        self.assertRaises(Exception, self.sg_service.delete_security_group, sg)

    # def test_instance_sg(self):
    #     instance = Mock()
    #     instance.security_groups = [Mock(), Mock()]
    #     self.sg_service.delete_all_security_groups_of_instance(instance)
    #     self.assertTrue(instance.security_groups[0].delete.callled and instance.security_groups[1].delete.callled)

    def test_create_sg(self):
        ec2_session = Mock()
        self.sg_service.create_security_group(ec2_session, 'vpc', 'name')

        self.assertTrue(ec2_session.create_security_group.called_with(
            'name',
            SecurityGroupService.CLOUDSHELL_SECURITY_GROUP_DESCRIPTION,
            'vpc'))

    def test_get_sg_names(self):
        reservation_id = 'res'
        res = self.sg_service.get_sandbox_security_group_names(reservation_id=reservation_id)
        security_group_names = [SecurityGroupService.CLOUDSHELL_SANDBOX_DEFAULT_SG.format(reservation_id),
                                SecurityGroupService.CLOUDSHELL_SANDBOX_ISOLATED_FROM_SANDBOX_SG.format(reservation_id)]
        self.assertEqual(res, security_group_names)

    def test_get_default_sg_name(self):
        reservation_id = 'res'
        sg_name = self.sg_service.sandbox_default_sg_name(reservation_id=reservation_id)
        security_group_name = SecurityGroupService.CLOUDSHELL_SANDBOX_DEFAULT_SG.format(reservation_id)
        self.assertEqual(sg_name, security_group_name)

    def test_get_isolated_sg_name(self):
        reservation_id = 'res'
        sg_name = self.sg_service.sandbox_isolated_sg_name(reservation_id=reservation_id)
        security_group_name = SecurityGroupService.CLOUDSHELL_SANDBOX_ISOLATED_FROM_SANDBOX_SG.format(reservation_id)
        self.assertEqual(sg_name, security_group_name)

    def test_get_security_group_by_name(self):
        vpc = Mock()
        sg = Mock()
        sg.group_name = 'name'
        vpc.security_groups = Mock()
        vpc.security_groups.all = Mock(return_value=[sg])
        res = self.sg_service.get_security_group_by_name(vpc, 'name')

        self.assertEqual(res, sg)

        vpc.security_groups.all = Mock(return_value=[])
        res = self.sg_service.get_security_group_by_name(vpc, 'name')

        self.assertIsNone(res)

        vpc.security_groups.all = Mock(return_value=[sg, sg])
        self.assertRaises(ValueError, self.sg_service.get_security_group_by_name, vpc, 'name')

    def test_set_shared_reservation_security_group_rules(self):
        sg = Fake()
        sg.id = 'id'
        sg.authorize_ingress = Mock()

        isolated_sg = Mock()
        isolated_sg.id = 'dummy'

        self.sg_service.set_shared_reservation_security_group_rules(sg, 'man',isolated_sg, True)

        self.assertTrue(sg.authorize_ingress.called_with(IpPermissions=[
            {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'UserIdGroupPairs': [
                    {
                        'GroupId': 'man'
                    }
                ]
            }, {
            'IpProtocol': '-1',
            'FromPort': -1,
            'ToPort': -1,
            'UserIdGroupPairs': [
                {
                    'GroupId': 'id'
                },
                {
                    'GroupId': 'dummy'
                }
            ]
        }
        ]))

    def test_set_isolated_reservation_security_group_rules(self):
        sg = Fake()
        sg.id = 'id'
        sg.authorize_ingress = Mock()
        self.sg_service.set_isolated_security_group_rules(sg, 'man', True)

        self.assertTrue(sg.authorize_ingress.called_with(IpPermissions=
        [
            {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'UserIdGroupPairs': [
                    {
                        'GroupId': 'man'
                    }
                ]
            }
        ]))

    def test_set_sg_security_group_rules(self):
        sg = Mock()
        port_data_in = Mock()
        port_data_in.from_port = 1
        port_data_in.to_port = 10
        inboud = [port_data_in]
        port_data_out = Mock()
        port_data_out.from_port = 1
        port_data_out.to_port = 10
        outboud = [port_data_out]

        self.sg_service.set_security_group_rules(sg, inboud, outboud)

        self.assertTrue(
            sg.security_group.authorize_egress.called_with([self.sg_service.get_ip_permission_object(port_data_out)]))
        self.assertTrue(
            sg.security_group.authorize_ingress.called_with([self.sg_service.get_ip_permission_object(port_data_in)]))

    def test_remove_allow_all_outbound_rule(self):
        sg = Mock()
        self.sg_service.remove_allow_all_outbound_rule(security_group=sg)
        sg.revoke_egress.assert_called_with(IpPermissions=[{
            'IpProtocol': '-1',
            'FromPort': 0,
            'ToPort': 65535,
            'IpRanges': [
                {
                    'CidrIp': '0.0.0.0/0'
                }
            ]
        }])


class Fake (object):
    pass

import uuid

from cloudshell.cp.aws.domain.services.ec2.tags import IsolationTagValues, TagService
from cloudshell.cp.aws.domain.services.ec2.tags import TypeTagValues
from cloudshell.cp.aws.models.port_data import PortData
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class SecurityGroupService(object):
    def __init__(self, tag_service):
        """
        :param TagService tag_service:
        :return:
        """
        self.tag_service = tag_service

    CLOUDSHELL_SANDBOX_DEFAULT_SG = "Cloudshell Sandbox SG {0}"
    CLOUDSHELL_SANDBOX_ISOLATED_FROM_SANDBOX_SG = "Isolated SG {0}"
    CLOUDSHELL_CUSTOM_SECURITY_GROUP = "Cloudshell Custom SG {0}"
    CLOUDSHELL_SECURITY_GROUP_DESCRIPTION = "Cloudshell Security Group"

    def delete_security_group(self, sg):
        if sg.group_name != 'default':
            sg.delete()
        return True

    def create_security_group(self, ec2_session, vpc_id, security_group_name):
        """
        creating a security group
        :param ec2_session:
        :param str vpc_id:
        :param str security_group_name:
        :return:
        """
        return ec2_session.create_security_group(GroupName=security_group_name,
                                                 Description=SecurityGroupService.CLOUDSHELL_SECURITY_GROUP_DESCRIPTION,
                                                 VpcId=vpc_id)

    @staticmethod
    def get_sandbox_security_group_names(reservation_id):
        return [SecurityGroupService.CLOUDSHELL_SANDBOX_DEFAULT_SG.format(reservation_id),
                SecurityGroupService.CLOUDSHELL_SANDBOX_ISOLATED_FROM_SANDBOX_SG.format(reservation_id)]

    @staticmethod
    def sandbox_default_sg_name(reservation_id):
        return SecurityGroupService.CLOUDSHELL_SANDBOX_DEFAULT_SG.format(reservation_id)

    @staticmethod
    def sandbox_isolated_sg_name(reservation_id):
        return SecurityGroupService.CLOUDSHELL_SANDBOX_ISOLATED_FROM_SANDBOX_SG.format(reservation_id)

    @staticmethod
    def get_security_group_by_name(vpc, name):
        security_groups = [sg
                           for sg in list(vpc.security_groups.all())
                           if sg.group_name == name]

        if not security_groups:
            return None

        if len(security_groups) > 1:
            raise ValueError('Too many security groups by that name')

        return security_groups[0]

    def set_shared_reservation_security_group_rules(self,
                                                    security_group,
                                                    management_sg_id,
                                                    isolated_sg,
                                                    need_management_sg):
        """
        Set inbound rules for the reservation shared security group.
        The default rules are:
         1) Allow all inbound traffic from instances with the same reservation id (inner sandbox connectivity)
         2) Allow all inbound traffic from the management vpc for specific security group id
        :param bool need_management_sg:
        :param security_group: security group object
        :param str management_sg_id: Id of the management security group id
        :return:
        """

        # management_rule = {'IpProtocol': '-1', 'FromPort': -1, 'ToPort': -1,
        #                    'UserIdGroupPairs': [{'GroupId': management_sg_id}]}
        #
        # allow_internal_traffic_rule = {'IpProtocol': '-1', 'FromPort': -1, 'ToPort': -1,
        #        'UserIdGroupPairs': [{'GroupId': security_group.id}, {'GroupId': isolated_sg.id}]}
        #
        # ip_permissions = [allow_internal_traffic_rule]
        #
        # if need_management_sg:
        #     ip_permissions.append(management_rule)
        management_rule = {'IpProtocol': '-1', 'FromPort': -1, 'ToPort': -1,
                           'UserIdGroupPairs': [{'GroupId': management_sg_id}]}

        allow_internal_traffic_rule = {'IpProtocol': '-1', 'FromPort': -1, 'ToPort': -1,
               'UserIdGroupPairs': [{'GroupId': security_group.id}, {'GroupId': isolated_sg.id}]}

        ip_permissions = [allow_internal_traffic_rule]

        if need_management_sg:
            ip_permissions.append(management_rule)

        security_group.authorize_ingress(IpPermissions=
                                         ip_permissions)

    def set_isolated_security_group_rules(self, security_group, management_sg_id, need_management_access):
        """
        Set inbound rules for the reservation isolated security group.
        The default rules are:
         1) Allow all inbound traffic from the management vpc for specific security group id
        :param bool need_management_access:
        :param security_group: security group object
        :param str management_sg_id: Id of the management security group id
        :return:
        """
        # security_group.authorize_ingress(IpPermissions=
        # [
        #     {
        #         'IpProtocol': '-1',
        #         'FromPort': -1,
        #         'ToPort': -1,
        #         'UserIdGroupPairs': [
        #             {
        #                 'GroupId': management_sg_id
        #             }
        #         ]
        #     }
        # ])
        if need_management_access:
            ip_permissions = [{'IpProtocol': '-1', 'FromPort': -1, 'ToPort': -1, 'UserIdGroupPairs': [{'GroupId': management_sg_id}]}]
            security_group.authorize_ingress(IpPermissions=ip_permissions)

    def set_security_group_rules(self, security_group, inbound_ports=None, outbound_ports=None, logger=None):
        """
        :param security_group: AWS SG object
        :param list[PortData] inbound_ports:
        :param list[PortData] outbound_ports:
        :param logging.Logger logger:
        :return:
        """
        # adding inbound port rules
        if inbound_ports:
            self._set_inbound_ports(inbound_ports, security_group)
            if logger:
                logger.info("Inbound ports attribute: {0} set to security group: {1}".format(inbound_ports,
                                                                                             security_group.group_id))

        # adding outbound port rules
        if outbound_ports:
            self._set_outbound_ports(outbound_ports, security_group)
            if logger:
                logger.info("Outbound ports attribute: {0} set to security group: {1}".format(outbound_ports,
                                                                                              security_group.group_id))

    def _set_outbound_ports(self, outbound_ports, security_group):
        if outbound_ports:
            ip_permissions = [self.get_ip_permission_object(port) for port in outbound_ports if port is not None]
            security_group.authorize_egress(IpPermissions=ip_permissions)

    def _set_inbound_ports(self, inbound_ports, security_group):
        if inbound_ports:
            ip_permissions = [self.get_ip_permission_object(port) for port in inbound_ports if port is not None]
            security_group.authorize_ingress(IpPermissions=ip_permissions)

    def remove_all_inbound_rules(self, security_group):
        rules = security_group.ip_permissions
        if rules:
            security_group.revoke_ingress(IpPermissions=rules)  # , GroupName=security_group.group_name)

    def remove_allow_all_outbound_rule(self, security_group):
        security_group.revoke_egress(IpPermissions=[{
            'IpProtocol': '-1',
            'FromPort': 0,
            'ToPort': 65535,
            'IpRanges': [
                {
                    'CidrIp': '0.0.0.0/0'
                }
            ]
        }])

    @staticmethod
    def get_ip_permission_object(port_data):
        return {
            'IpProtocol': port_data.protocol,
            'FromPort': int(port_data.from_port),
            'ToPort': int(port_data.to_port),
            'IpRanges': [
                {
                    'CidrIp': port_data.destination
                }
            ]}

    def get_inbound_ports_security_group(self, ec2_session, network_interface):
        """
        Returns an inbound ports security group for the nic
        Inbound ports security group is defined by the following attributes and their values:
        "Isolation=Exclusive" and "Type=InboundPorts"
        :param ec2_session:
        :param network_interface: AWS::EC2::NetworkInterface
        :rtype AppSecurityGroupModel:
        """
        security_group_descriptions = network_interface.groups

        for security_group_description in security_group_descriptions:
            security_group = ec2_session.SecurityGroup(security_group_description['GroupId'])
            if SecurityGroupService._is_inbound_ports_security_group(self.tag_service, security_group):
                return security_group

        return None

    def get_custom_security_group(self, ec2_session,  network_interface):
        """
        Returns a custom security group for the nic
        Custom security group is defined by the following attributes and their values:
        "Isolation=Exclusive" and "Type=Interface"
        :param ec2_session:
        :param network_interface: AWS::EC2::NetworkInterface
        :rtype AppSecurityGroupModel:
        """
        security_group_descriptions = network_interface.groups

        for security_group_description in security_group_descriptions:
            security_group = ec2_session.SecurityGroup(security_group_description['GroupId'])
            if SecurityGroupService._is_custom_security_group(self.tag_service, security_group):
                return security_group

        return None

    def get_or_create_custom_security_group(self, ec2_session, logger, network_interface, reservation, vpc_id):
        """
        Returns or create (if doesn't exist) and then returns a custom security group for the nic
        Custom security group is defined by the following attributes and their values:
        "Isolation=Exclusive" and "Type=Interface"
        :param ec2_session:
        :param logging.Logger logger:
        :param network_interface: AWS::EC2::NetworkInterface
        :param ReservationModel reservation:
        :param str vpc_id:
        :rtype AppSecurityGroupModel:
        """

        security_group_descriptions = network_interface.groups

        custom_security_group = self.get_custom_security_group(ec2_session=ec2_session,
                                                               network_interface=network_interface)

        if custom_security_group:
            logger.info("Custom security group exists for nic '{}'.".format(network_interface.network_interface_id))
            return custom_security_group

        # name for a new (non existed yet) custom security group
        security_group_name = SecurityGroupService.CLOUDSHELL_CUSTOM_SECURITY_GROUP.format(str(uuid.uuid4()))

        # create a new security group in vpc
        custom_security_group = self.create_security_group(ec2_session, vpc_id, security_group_name)

        logger.info("Custom security group '{}' created.".format(security_group_name))

        # add tags to the created security group that will define it as a custom security group
        default_tags = self.tag_service.get_default_tags(security_group_name, reservation)
        custom_tags = self.tag_service.get_custom_security_group_tags()
        all_tags = default_tags + custom_tags
        self.tag_service.set_ec2_resource_tags(custom_security_group, all_tags)

        # attach the custom security group to the nic
        custom_security_group_id = custom_security_group.group_id
        security_group_ids = [x['GroupId'] for x in security_group_descriptions]
        security_group_ids.append(custom_security_group_id)
        network_interface.modify_attribute(Groups=security_group_ids)

        return custom_security_group

    @staticmethod
    def _is_inbound_ports_security_group(tag_service, security_group):
        if not isinstance(security_group.tags, list):
            return False
        isolation_tag = tag_service.find_isolation_tag_value(security_group.tags)
        type_tag = tag_service.find_type_tag_value(security_group.tags)
        return isolation_tag == IsolationTagValues.Exclusive and type_tag == TypeTagValues.InboundPorts

    @staticmethod
    def _is_custom_security_group(tag_service, security_group):
        if not isinstance(security_group.tags, list):
            return False
        isolation_tag = tag_service.find_isolation_tag_value(security_group.tags)
        type_tag = tag_service.find_type_tag_value(security_group.tags)
        return isolation_tag == IsolationTagValues.Exclusive and type_tag == TypeTagValues.Interface

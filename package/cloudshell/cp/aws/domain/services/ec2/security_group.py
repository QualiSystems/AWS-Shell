from cloudshell.cp.aws.models.port_data import PortData


class SecurityGroupService(object):
    CLOUDSHELL_SANDBOX_SG = "Cloudshell Sandbox SG {0}"
    CLOUDSHELL_CUSTOM_SECURITY_GROUP = "Cloudshell Custom SG {0}"
    CLOUDSHELL_SECURITY_GROUP_DESCRIPTION = "Cloudshell Security Group"

    def delete_security_group(self, sg):
        if sg.group_name != 'default':
            sg.delete()
        return True

    def delete_all_security_groups_of_instance(self, instance):
        if instance.security_groups:
            for security_group in instance.security_groups:
                self.delete_security_group(security_group)

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
    def get_sandbox_security_group_name(reservation_id):
        return SecurityGroupService.CLOUDSHELL_SANDBOX_SG.format(reservation_id)

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

    def set_shared_reservation_security_group_rules(self, security_group, management_sg_id):
        """
        Set inbound rules for the reservation shared security group.
        The default rules are:
         1) Allow all inbound traffic from instances with the same reservation id (inner sandbox connectivity)
         2) Allow all inbound traffic from the management vpc for specific security group id
        :param security_group: security group object
        :param str management_sg_id: Id of the management security group id
        :return:
        """
        security_group.authorize_ingress(IpPermissions=
        [
            {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'UserIdGroupPairs': [
                    {
                        'GroupId': management_sg_id
                    }
                ]
            },
            {
                'IpProtocol': '-1',
                'FromPort': -1,
                'ToPort': -1,
                'UserIdGroupPairs': [
                    {
                        'GroupId': security_group.id
                    }
                ]
            }
        ])

    def set_security_group_rules(self, security_group, inbound_ports, outbound_ports):
        """
        :param security_group: AWS SG object
        :param list[PortData] inbound_ports:
        :param list[PortData] outbound_ports:
        :return:
        """
        # adding inbound port rules
        if inbound_ports:
            self._set_inbound_ports(inbound_ports, security_group)

        # adding outbound port rules
        if outbound_ports:
            self._set_outbound_ports(outbound_ports, security_group)

    def _set_outbound_ports(self, outbound_ports, security_group):
        if outbound_ports:
            ip_permissions = [self.get_ip_permission_object(port) for port in outbound_ports if port is not None]
            security_group.authorize_egress(IpPermissions=ip_permissions)

    def _set_inbound_ports(self, inbound_ports, security_group):
        if inbound_ports:
            ip_permissions = [self.get_ip_permission_object(port) for port in inbound_ports if port is not None]
            security_group.authorize_ingress(IpPermissions=ip_permissions)

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

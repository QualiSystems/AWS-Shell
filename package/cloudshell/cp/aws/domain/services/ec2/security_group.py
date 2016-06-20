from cloudshell.cp.aws.models.port_data import PortData


class AWSSecurityGroupService(object):
    QUALI_SECURITY_GROUP = "Quali_security_group"
    QUALI_SECURITY_GROUP_DESCRIPTION = "Quali Security Group"

    @staticmethod
    def delete_security_group(security_group):
        try:
            security_group.delete()
        except Exception:
            raise

    def delete_all_security_groups_of_instance(self, instance):
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
                                                 Description=AWSSecurityGroupService.QUALI_SECURITY_GROUP_DESCRIPTION,
                                                 VpcId=vpc_id)

    @staticmethod
    def get_security_group_name(reservation_id):
        return 'quali_sandbox_security_group_{0}'.format(reservation_id)

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

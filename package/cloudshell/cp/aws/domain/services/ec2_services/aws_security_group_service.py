from cloudshell.cp.aws.domain.services.model_parser.port_group_attribute_parser import PortGroupAttributeParser


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

    @staticmethod
    def create_security_group(aws_session, ec2_session, vpc, security_group_name):
        # creating the security group
        security_group = aws_session.create_security_group(ec2_session,
                                                           security_group_name,
                                                           AWSSecurityGroupService.QUALI_SECURITY_GROUP_DESCRIPTION,
                                                           vpc)
        return security_group

    def set_security_group_rules(self, ami_deployment_model, security_group):
        # adding inbound port rules
        if ami_deployment_model.inbound_ports:
            inbound_ports = PortGroupAttributeParser.parse_port_group_attribute(ami_deployment_model.inbound_ports)
            self._set_inbound_ports(inbound_ports, security_group)

        # adding outbound port rules
        if ami_deployment_model.outbound_ports:
            outbound_ports = PortGroupAttributeParser.parse_port_group_attribute(ami_deployment_model.outbound_ports)
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



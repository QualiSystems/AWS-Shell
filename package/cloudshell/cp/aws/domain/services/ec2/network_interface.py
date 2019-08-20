class NetworkInterfaceService(object):
    def __init__(self, subnet_service):
        """
        :param SubnetService subnet_service: Subnet Service
        :return:
        """
        self.subnet_service = subnet_service

    def get_network_interface_for_single_subnet_mode(self, add_public_ip, security_group_ids, vpc):
        """
        :param bool add_public_ip:
        :param list[str] security_group_ids:
        :param vpc: VPC instance
        :return:
        """
        return self.build_network_interface_dto(
                subnet_id=self.subnet_service.get_first_subnet_from_vpc(vpc).subnet_id,
                device_index=0,
                groups=security_group_ids,
                public_ip=add_public_ip)

    def build_network_interface_dto(self, subnet_id, device_index, groups, public_ip=None):
        net_if = {
            'SubnetId': subnet_id,
            'DeviceIndex': device_index,
            'Groups': groups
        }

        if public_ip is not None:
            net_if['AssociatePublicIpAddress'] = public_ip

        return net_if

    def find_network_interface(self, vpc, private_ip):
        result = vpc.network_interfaces.find(Filters=[{'Name': 'private-ip-address', 'Values': [private_ip]}])
        return result[0] if result else None


class NetworkInterfaceService(object):
    def __init__(self, subnet_service):
        """
        :param SubnetService subnet_service: Subnet Service
        :return:
        """
        self.subnet_service = subnet_service

    def get_network_interface_for_single_subnet_mode(self, add_public_ip, security_group_ids, vpc, private_ip=None):
        """
        :param bool add_public_ip:
        :param list[str] security_group_ids:
        :param vpc: VPC instance
        :param str private_ip:
        :return:
        """
        return self.build_network_interface_dto(
                subnet_id=self.subnet_service.get_first_subnet_from_vpc(vpc).subnet_id,
                device_index=0,
                groups=security_group_ids,
                public_ip=add_public_ip,
                private_ip=private_ip)

    def build_network_interface_dto(self, subnet_id, device_index, groups, public_ip=None, private_ip=None):
        net_if = {
            'SubnetId': subnet_id,
            'DeviceIndex': device_index,
            'Groups': groups
        }

        if public_ip:
            net_if['AssociatePublicIpAddress'] = public_ip

        if private_ip:
            net_if['PrivateIpAddress'] = private_ip

        return net_if

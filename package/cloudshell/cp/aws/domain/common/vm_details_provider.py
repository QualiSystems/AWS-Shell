class VmDetailsProvider(object):
    def __init__(self):
        pass

    def create(self, instance):
        vm_details = VmDetails()

        vm_details.vm_instance_data = self._get_vm_instance_data(instance, instance.vpc_id)
        vm_details.vm_network_data = self._get_vm_network_data(instance)
        return vm_details

    def _get_vm_instance_data(self, instance, vpc_id):
        # if not windows, instance platform is empty; therefore we default to linux
        platform = instance.platform or 'linux'
        volume = self._get_volume(instance)
        data = [AdditionalData('AMI ID', instance.image_id),
                AdditionalData('instance type', instance.instance_type),
                AdditionalData('platform', platform),
                AdditionalData('Storage Name', self._get_volume_id(volume)),
                AdditionalData('Storage Type', self._get_volume_type(volume)),
                AdditionalData('Storage Size', self._get_volume_size(volume)),
                AdditionalData('VPC ID', vpc_id, hidden=True),
                AdditionalData('Availability Zone', self._get_availability_zone(instance), hidden=True)
                ]
        return data

    def _get_vm_network_data(self, instance):
        network_interface_objects = []

        instance.reload()
        if instance.network_interfaces:
            network_interfaces = sorted(instance.network_interfaces, key=lambda x: x.attachment.get("DeviceIndex"))
            for network_interface in network_interfaces:
                network_interface_object = {
                    "interface_id": network_interface.network_interface_id,
                    "network_id": network_interface.subnet_id,
                    "network_data": [AdditionalData("IP", network_interface.private_ip_address)]
                }

                is_attached_to_elastic_ip = self._has_elastic_ip(network_interface)
                is_primary = self._is_primary_interface(network_interface)
                public_ip = self._calculate_public_ip(network_interface)

                if is_primary:
                    network_interface_object["is_primary"] = is_primary

                network_interface_object["network_data"].append(AdditionalData("Public IP", public_ip))
                network_interface_object["network_data"].append(AdditionalData("Elastic IP", is_attached_to_elastic_ip))

                network_interface_object["network_data"].append(AdditionalData("MAC Address", network_interface.mac_address))

                network_interface_objects.append(network_interface_object)


        # TODO sort by device index
        return network_interface_objects

    def _calculate_public_ip(self, interface):
        # interface has public ip if:
        # a. is elastic ip
        # b. not elastic, but primary and instance has public ip

        if interface.association_attribute!=None and "PublicIp" in interface.association_attribute:
            return interface.association_attribute.get("PublicIp")
        return ""

    def _has_elastic_ip(self, interface):
        # IpOwnerId: amazon - temporary public ip
        # IpOwnerId: some guid - elastic ip
        return interface.association_attribute!=None and 'IpOwnerId' in interface.association_attribute \
               and interface.association_attribute.get('IpOwnerId') != 'amazon'

    def _is_primary_interface(self, interface):
        return interface.attachment.get("DeviceIndex") == 0

    @staticmethod
    def _get_volume(instance):
        return next((v for v in instance.volumes.all()), None)

    def _get_availability_zone(self, instance):
        return instance.placement.get('AvailabilityZone', None)

    def _get_volume_size(self, volume):
        return '{0} {1}'.format(volume.size, 'GiB') if volume else None

    def _get_volume_type(self, volume):
        return volume.volume_type if volume else None

    def _get_volume_id(self, volume):
        return volume.volume_id if volume else None


class VmDetails(object):
    def __init__(self):
        self.vm_instance_data = {} # type: dict
        self.vm_network_data = [] # type: list[VmNetworkData]


class VmNetworkData(object):
    def __init__(self):
        self.interface_id = {} # type: str
        self.network_id = {} # type: str
        self.is_primary = False # type: bool
        self.network_data = {} # type: dict


def AdditionalData(key, value, hidden=False):
    """
    :type key: str
    :type value: str
    :type hidden: bool
    """
    return {
        "key": key,
        "value": value,
        "hidden": hidden
    }

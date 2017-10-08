
class VmDetailsProvider(object):
    def __init__(self):
        pass

    def create(self, instance):
        vm_details = VmDetails()
        vm_details.vm_instance_data = self._get_vm_instance_data(instance)
        vm_details.vm_network_data = self._get_vm_network_data(instance)
        return vm_details

    def _get_vm_instance_data(self, instance):
        data = {
            'ami_id': instance.image_id,
            'instance_type': instance.instance_type
        }
        platform = instance.platform
        if platform:
            data['platform'] = platform
        return data

    def _get_vm_network_data(self, instance):
        network_interface_objects = []

        if instance.network_interfaces:
            for network_interface in instance.network_interfaces:
                network_interface_object = {
                    "interface_id": network_interface.network_interface_id,
                    "network_id": network_interface.subnet_id,
                    "network_data": {
                        "mac_address": network_interface.mac_address,
                        "device_index": network_interface.attachment.get("DeviceIndex"),
                        "private_ip": network_interface.private_ip_address,
                    }
                }

                is_attached_to_elastic_ip = self._has_elastic_ip(network_interface)
                is_primary = self._is_primary_interface(network_interface)
                public_ip = self._calculate_public_ip(network_interface, instance)

                if is_attached_to_elastic_ip:
                    network_interface_object["network_data"]["is_elastic_ip"] = is_attached_to_elastic_ip
                if is_primary:
                    network_interface_object["is_primary"] = is_primary
                if public_ip:
                    network_interface_object["network_data"]["public_ip"] = public_ip

                network_interface_objects.append(network_interface_object)

        return network_interface_objects

    def _calculate_public_ip(self, interface, instance):
        # interface has public ip if:
        # a. is elastic ip
        # b. not elastic, but primary and instance has public ip

        if self._has_elastic_ip(interface):
            return interface.association_attribute.get("PublicIp")
        if self._is_primary_interface(interface):
            return instance.public_ip_address
        return None

    def _has_elastic_ip(self, interface):
        # allocationid is used to associate elastic ip with ec2 instance
        return interface.association_attribute and 'AllocationId' in interface.association_attribute

    def _is_primary_interface(self, interface):
        return interface.attachment.get("DeviceIndex") == 0


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
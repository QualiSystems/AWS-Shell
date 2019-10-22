from cloudshell.cp.core.models import VmDetailsProperty, VmDetailsNetworkInterface, VmDetailsData


class VmDetailsProvider(object):
    def __init__(self):
        pass

    def create(self, instance, deploy_app_name=""):
        vm_instance_data = self._get_vm_instance_data(instance, instance.vpc_id)
        vm_network_data = self._get_vm_network_data(instance)

        return VmDetailsData(vmInstanceData=vm_instance_data, vmNetworkData=vm_network_data, appName=deploy_app_name)

    def _get_vm_instance_data(self, instance, vpc_id):
        # if not windows, instance platform is empty; therefore we default to linux
        platform = instance.platform or 'linux'
        volume = self._get_volume(instance)
        data = [VmDetailsProperty(key='AMI ID', value=instance.image_id),
                VmDetailsProperty(key='instance type', value=instance.instance_type),
                VmDetailsProperty(key='platform', value=platform),
                VmDetailsProperty(key='Storage Name', value=self._get_volume_id(volume)),
                VmDetailsProperty(key='Storage Type', value=self._get_volume_type(volume)),
                VmDetailsProperty(key='Storage Size', value=self._get_volume_size(volume)),
                VmDetailsProperty(key='VPC ID', value=vpc_id, hidden=True),
                VmDetailsProperty(key='Availability Zone', value=self._get_availability_zone(instance), hidden=True)]

        if instance.iam_instance_profile:
            arn = instance.iam_instance_profile["Arn"]
            instance_profile_name = arn.split('instance-profile/')[-1]
            data.append(VmDetailsProperty(key='IAM Role', value=instance_profile_name))

        return data

    def _get_vm_network_data(self, instance):
        network_interfaces_results = []

        instance.reload()

        if not instance.network_interfaces:
            return network_interfaces_results

        network_interfaces = sorted(instance.network_interfaces, key=lambda x: x.attachment.get("DeviceIndex"))

        for network_interface in network_interfaces:
            is_attached_to_elastic_ip = self._has_elastic_ip(network_interface)
            is_primary = self._is_primary_interface(network_interface)
            public_ip = self._calculate_public_ip(network_interface)

            network_data = [VmDetailsProperty(key="IP", value=network_interface.private_ip_address),
                            VmDetailsProperty(key="Public IP", value=public_ip),
                            VmDetailsProperty(key="Elastic IP", value=is_attached_to_elastic_ip),
                            VmDetailsProperty(key="MAC Address", value=network_interface.mac_address),
                            VmDetailsProperty(key="NIC", value=network_interface.network_interface_id),
                            VmDetailsProperty(key="Device Index",
                                              value=network_interface.attachment.get("DeviceIndex"))]

            current_interface = VmDetailsNetworkInterface(interfaceId=network_interface.network_interface_id,
                                                          networkId=network_interface.subnet_id,
                                                          isPrimary=is_primary, networkData=network_data,
                                                          privateIpAddress=network_interface.private_ip_address,
                                                          publicIpAddress=public_ip)

            network_interfaces_results.append(current_interface)

        return network_interfaces_results

    def _calculate_public_ip(self, interface):
        # interface has public ip if:
        # a. is elastic ip
        # b. not elastic, but primary and instance has public ip

        if interface.association_attribute != None and "PublicIp" in interface.association_attribute:
            return interface.association_attribute.get("PublicIp")
        return ""

    def _has_elastic_ip(self, interface):
        # IpOwnerId: amazon - temporary public ip
        # IpOwnerId: some guid - elastic ip
        return interface.association_attribute != None and 'IpOwnerId' in interface.association_attribute \
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

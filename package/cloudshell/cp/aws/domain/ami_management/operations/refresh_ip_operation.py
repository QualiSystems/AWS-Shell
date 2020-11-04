from cloudshell.api.cloudshell_api import CloudShellAPISession


class RefreshIpOperation(object):
    PUBLIC_IP = "Public IP"

    def __init__(self, instance_service):
        """
        :param instance_service: Instance Service
        :type instance_service: cloudshell.cp.aws.domain.services.ec2.instance.InstanceService
        """
        self.instance_service = instance_service

    def refresh_ip(self, cloudshell_session, ec2_session, deployed_instance_id, private_ip_on_resource,
                   public_ip_on_resource, public_ip_attribute_name, resource_fullname):
        """

        :param CloudShellAPISession cloudshell_session:
        :param ec2_session : ec2_session
        :param deployed_instance_id:
        :param private_ip_on_resource:
        :param public_ip_on_resource:
        :param public_ip_attribute_name:
        :param resource_fullname:
        """

        deployed_instance = self.instance_service.get_active_instance_by_id(ec2_session, deployed_instance_id)

        public_ip_on_aws = deployed_instance.public_ip_address
        private_ip_on_aws = deployed_instance.private_ip_address

        if not public_ip_on_aws:
            # find first elastic ip
            sorted_network_interfaces_attribute = \
                sorted(deployed_instance.network_interfaces_attribute, key=lambda x: x["Attachment"]["DeviceIndex"])
            for net in sorted_network_interfaces_attribute:
                if "Association" in net and "PublicIp" in net["Association"] and net["Association"]["PublicIp"]:
                    public_ip_on_aws = net["Association"]["PublicIp"]
                    break
        if public_ip_attribute_name \
                and public_ip_on_aws \
                and public_ip_on_aws != public_ip_on_resource:
            cloudshell_session.SetAttributeValue(resource_fullname, public_ip_attribute_name,
                                                 public_ip_on_aws if public_ip_on_aws is not None else "")

        if private_ip_on_aws != private_ip_on_resource:
            cloudshell_session.UpdateResourceAddress(resource_fullname, private_ip_on_aws)

import boto3
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.models.app_security_groups_model import AppSecurityGroupModel


class SetAppSecurityGroupsOperation(object):
    def __init__(self, instance_service, tag_service, security_group_service):
        """
        :param InstanceService instance_service:
        :param TagService tag_service:
        :type instance_service: cloudshell.cp.aws.domain.services.ec2.instance.InstanceService
        :param security_group_service:
        :type security_group_service: cloudshell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :return:
        """
        self.tag_service = tag_service
        self.instance_service = instance_service
        self.security_group_service = security_group_service

    def set_app_security_groups(self, app_security_group_model, ec2_session):
        """
        Set custom security groups to a deployed app
        :param AppSecurityGroupModel app_security_group_model:
        :param boto3.resources.base.ServiceResource ec2_session:
        :return:
        """

        """
        - get vm id from deployed app details
        - for each security_groups_configuration
        - - get subnet id
        - - get nic (s) !!!
            for each nic !!!
                - - if custom security group exists --> overwrite it
                - - if custom security group doesn't exist
                - - - create a new security group
                - - - attach it to the nic
                - - - add (from input) rules to the security group
                - - - go to the next nic
        
        """

        vm_id = app_security_group_model.deployed_app.vm_details.uid
        instance = self.instance_service.get_active_instance_by_id(ec2_session, vm_id)
        security_group_configurations = app_security_group_model.security_group_configurations

        for security_group_configuration in security_group_configurations:
            subnet_id = security_group_configuration.subnet_id
            network_interfaces = filter(lambda x: x["SubnetId "] == subnet_id,
                                        instance.network_interfaces_attribute)
            for network_interface in network_interfaces:
                custom_security_group = self.security_group_service.get_or_create_custom_security_group(network_interface)


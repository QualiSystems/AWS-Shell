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

    def set_apps_security_groups(self, app_security_group_models, ec2_session, logger):
        """
        Set custom security groups to a deployed app
        :param lis[AppSecurityGroupModel] app_security_group_models:
        :param boto3.resources.base.ServiceResource ec2_session:
        :param logging.Logger logger:
        :return:
        """

        for app_security_group_model in app_security_group_models:
            vm_id = app_security_group_model.deployed_app.vm_details.uid
            instance = self.instance_service.get_active_instance_by_id(ec2_session, vm_id)
            vpc_id = instance.vpc_id
            security_group_configurations = app_security_group_model.security_group_configurations

            logger.info("Setting custom app security rules for {}.".format(app_security_group_model.deployed_app.name))

            for security_group_configuration in security_group_configurations:
                subnet_id = security_group_configuration.subnet_id
                network_interfaces = filter(lambda x: x.subnet_id == subnet_id, instance.network_interfaces)
                for network_interface in network_interfaces:
                    custom_security_group = self.security_group_service.get_or_create_custom_security_group(ec2_session, logger, network_interface, vpc_id)
                    self.security_group_service.set_security_group_rules(custom_security_group, security_group_configuration.rules)


import uuid

from cloudshell.cp.aws.device_access_layer.models.ami_deployment_model import AMIDeploymentModel
from cloudshell.cp.aws.device_access_layer.aws_api import AWSApi
from cloudshell.cp.aws.domain.services.ec2_services.aws_security_group_service import \
    AWSSecurityGroupService
from cloudshell.cp.aws.domain.services.ec2_services.tag_creator_service import TagCreatorService, IsolationTagValues


class DeployAMIOperation(object):
    def __init__(self, aws_api, security_group_service, tag_creator_service):
        """
        :param TagCreatorService tag_creator_service:
        :param AWSApi aws_api: the AWS API
        :param AWSSecurityGroupService security_group_service: service that handel the creation of security group
        :return:
        """

        self.tag_creator_service = tag_creator_service
        self.aws_api = aws_api
        self.security_group_service = security_group_service

    def deploy(self, ec2_session, name, reservation_id, aws_ec2_cp_resource_model, ami_deployment_model):
        """
        :param name: The name of the deployed ami
        :type name: str
        :param reservation_id:
        :type reservation_id: str
        :param ec2_session:
        :param aws_ec2_cp_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_cp_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """

        security_group = self._create_security_group_for_instance(ami_deployment_model=ami_deployment_model,
                                                                  aws_ec2_cp_resource_model=aws_ec2_cp_resource_model,
                                                                  ec2_session=ec2_session,
                                                                  reservation_id=reservation_id)

        ami_deployment_info = self._create_deployment_parameters(aws_ec2_cp_resource_model,
                                                                 ami_deployment_model,
                                                                 security_group)

        return self.aws_api.create_instance(ec2_session=ec2_session,
                                            name=name,
                                            reservation_id=reservation_id,
                                            ami_deployment_info=ami_deployment_info)

    def _create_security_group_for_instance(self, ami_deployment_model, aws_ec2_cp_resource_model, ec2_session,
                                            reservation_id):

        if not ami_deployment_model.inbound_ports and not ami_deployment_model.outbound_ports:
            return None

        security_group_name = AWSSecurityGroupService.QUALI_SECURITY_GROUP + " " + str(uuid.uuid4())

        security_group = self.security_group_service.create_security_group(ec2_session,
                                                                           aws_ec2_cp_resource_model.vpc,
                                                                           security_group_name)

        tags = self.tag_creator_service.get_security_group_tags(name=security_group_name,
                                                                isolation=IsolationTagValues.Exclusive,
                                                                reservation_id=reservation_id)

        self.aws_api.set_ec2_resource_tags(security_group, tags)

        self.security_group_service.set_security_group_rules(ami_deployment_model, security_group)

        return security_group

    def _create_deployment_parameters(self, aws_ec2_resource_model, ami_deployment_model, security_group):
        """
        :param aws_ec2_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param security_group : The security group of the AMI
        :type security_group : securityGroup
        """
        aws_model = AMIDeploymentModel()
        if not ami_deployment_model.aws_ami_id:
            raise ValueError('AWS Image Id cannot be empty')

        aws_model.aws_ami_id = ami_deployment_model.aws_ami_id
        aws_model.min_count = 1
        aws_model.max_count = 1
        aws_model.instance_type = ami_deployment_model.instance_type if ami_deployment_model.instance_type else aws_ec2_resource_model.default_instance_type
        aws_model.private_ip_address = ami_deployment_model.private_ip_address if ami_deployment_model.private_ip_address else None
        aws_model.block_device_mappings = self._get_block_device_mappings(ami_deployment_model, aws_ec2_resource_model)
        aws_model.aws_key = ami_deployment_model.aws_key
        aws_model.subnet_id = aws_ec2_resource_model.subnet

        if security_group is not None:
            aws_model.security_group_ids.append(security_group.group_id)
        return aws_model

    @staticmethod
    def _get_block_device_mappings(ami_rm, aws_ec2_rm):
        block_device_mappings = [
            {
                'DeviceName': ami_rm.device_name if ami_rm.device_name else aws_ec2_rm.device_name,
                'Ebs': {
                    'VolumeSize': int(ami_rm.storage_size if ami_rm.storage_size else aws_ec2_rm.default_storage_size),
                    'DeleteOnTermination': ami_rm.delete_on_termination if ami_rm.delete_on_termination else aws_ec2_rm.delete_on_termination,
                    'VolumeType': ami_rm.storage_type if ami_rm.storage_type else aws_ec2_rm.default_storage_type
                }
            }]
        return block_device_mappings

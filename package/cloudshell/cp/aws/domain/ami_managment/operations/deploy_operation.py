from cloudshell.cp.aws.device_access_layer.models.ami_deployment_model import AMIDeploymentModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult


class DeployAMIOperation(object):
    def __init__(self, aws_api):
        """
        :param aws_api this is the...
        :type aws_api: cloudshell.cp.aws.device_access_layer.aws_api.AWSApi
        """
        self.aws_api = aws_api

    def deploy(self, ec2_session, name, aws_ec2_cp_resource_model, ami_deployment_resource_model):
        """
        :param name: The name of the deployed ami
        :type name: str
        :param ec2_session:
        :param aws_ec2_cp_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_cp_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_resource_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_resource_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """

        ami_deployment_info = self._create_deployment_parameters(aws_ec2_cp_resource_model,
                                                                 ami_deployment_resource_model)

        return self.aws_api.create_instance(ec2_session, name, ami_deployment_info)




    def _create_deployment_parameters(self, aws_ec2_rm, ami_rm):
        """
        :param aws_ec2_rm: The resource model of the AMI deployment option
        :type aws_ec2_rm: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_rm: The resource model on which the AMI will be deployed on
        :type ami_rm: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        """
        aws_model = AMIDeploymentModel()
        if not ami_rm.aws_ami_id:
            raise ValueError('AWS Image Id cannot be empty')

        aws_model.aws_ami_id = ami_rm.aws_ami_id
        aws_model.min_count = 1
        aws_model.max_count = 1
        aws_model.instance_type = ami_rm.instance_type if ami_rm.instance_type else aws_ec2_rm.instance_type
        aws_model.private_ip_address = ami_rm.private_ip_address if ami_rm.private_ip_address else None
        aws_model.block_device_mappings = self._get_block_device_mappings(ami_rm, aws_ec2_rm)
        aws_model.aws_key = ami_rm.aws_key

        return aws_model

    @staticmethod
    def _get_block_device_mappings(ami_rm, aws_ec2_rm):
        block_device_mappings = [
            {
                'DeviceName': ami_rm.device_name if  ami_rm.device_name else aws_ec2_rm.device_name,
                'Ebs': {
                    'VolumeSize':int( ami_rm.storage_size if ami_rm.storage_size else aws_ec2_rm.storage_size),
                    'DeleteOnTermination': ami_rm.delete_on_termination if ami_rm.delete_on_termination else aws_ec2_rm.delete_on_termination,
                    'VolumeType': ami_rm.storage_type if ami_rm.storage_type else aws_ec2_rm.storage_type
                }
            }]
        return block_device_mappings

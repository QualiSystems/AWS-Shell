import jsonpickle

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.device_access_layer.aws_api import AWSApi
from cloudshell.cp.aws.domain.ami_managment.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.common.aws_session_manager import AWSSessionManager
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class AWSShell(object):
    def __init__(self):
        self.aws_api = AWSApi()
        self.credentials_manager = AWSSessionManager()
        self.deploy_ami_operation = DeployAMIOperation(self.aws_api)

    def deploy_ami(self, command_context, deployment_request):
        """
        Will deploy Amazon Image on the cloud provider
        :param name: The name of the instance
        :type name: str
        :param aws_ami_deployment_resource_model: The resource model of the AMI deployment option
        :type aws_ami_deployment_resource_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param aws_ec2_resource_model: The resource model on which the AMI will be deployed on
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        """

        aws_ami_deployment_resource_model,name= self._convert_to_deployment_resource_model(deployment_request)
        aws_ec2_resource_model = self.convert_to_aws_resource_model(command_context)

        user, access_key_id, pwd, secret_access_key, region = self.credentials_manager.get_credentials()
        ec2_session = self.aws_api.create_ec2_session(access_key_id, secret_access_key, region)
        self.deploy_ami_operation.deploy(ec2_session, name, aws_ec2_resource_model, aws_ami_deployment_resource_model)

    def convert_to_aws_resource_model(self, command_context):
        resource_context = command_context.resource.attributes
        aws_ec2_resource_model = AWSEc2CloudProviderResourceModel()
        aws_ec2_resource_model.storage_size = resource_context['Storage Size']
        aws_ec2_resource_model.storage_iops = resource_context['Storage IOPS']
        aws_ec2_resource_model.region = resource_context['Region']
        aws_ec2_resource_model.max_storage_iops = resource_context['Max Storage IOPS']
        aws_ec2_resource_model.max_storage_size = resource_context['Max Storage Size']
        return aws_ec2_resource_model

    def _convert_to_deployment_resource_model(self, deployment_request):
        data = jsonpickle.decode(deployment_request)
        data_holder = DeployDataHolder(data)
        deployment_resource_model=DeployAWSEc2AMIInstanceResourceModel()
        deployment_resource_model.aws_ec2 = data_holder.image_params.aws_ec2
        deployment_resource_model.aws_ami_id = data_holder.image_params.aws_ami_id
        deployment_resource_model.storage_size = data_holder.image_params.storage_size
        deployment_resource_model.storage_iops = data_holder.image_params.storage_iops
        deployment_resource_model.storage_type = data_holder.image_params.storage_type
        deployment_resource_model.min_count = int( data_holder.image_params.min_count)
        deployment_resource_model.max_count = int(data_holder.image_params.max_count)
        deployment_resource_model.instance_type = data_holder.image_params.instance_type
        deployment_resource_model.aws_key = data_holder.image_params.aws_key
        deployment_resource_model.security_group_ids = data_holder.image_params.security_group_ids
        deployment_resource_model.private_ip_address = data_holder.image_params.private_ip_address
        deployment_resource_model.device_name = data_holder.image_params.device_name
        deployment_resource_model.delete_on_termination = bool(data_holder.image_params.delete_on_termination)
        return deployment_resource_model,data_holder.app_name





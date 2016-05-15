import jsonpickle

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.device_access_layer.aws_api import AWSApi
from cloudshell.cp.aws.domain.ami_managment.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.common.aws_session_manager import AWSSessionManager


class AWSShell(object):
    def __init__(self):
        self.aws_api = AWSApi()
        self.credentials_manager = AWSSessionManager()
        self.deploy_ami_operation = DeployAMIOperation(self.aws_api)

    def deploy_ami(self, deployment_request):
        """
        Will deploy Amazon Image on the cloud provider
        :param name: The name of the instance
        :type name: str
        :param aws_ami_deployment_resource_model: The resource model of the AMI deployment option
        :type aws_ami_deployment_resource_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param aws_ec2_resource_model: The resource model on which the AMI will be deployed on
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        """

        data = jsonpickle.decode(deployment_request)
        data_holder = DeployDataHolder(data)
        #  name, aws_ec2_resource_model, aws_ami_deployment_resource_model
        name="resourcename"
        aws_ec2_resource_model=None
        aws_ami_deployment_resource_model=None

        user, access_key_id, pwd, secret_access_key, region = self.credentials_manager.get_credentials()
        ec2_session = self.aws_api.create_ec2_session(access_key_id, secret_access_key, region)
        self.deploy_ami_operation.deploy(ec2_session, name, aws_ec2_resource_model, aws_ami_deployment_resource_model)

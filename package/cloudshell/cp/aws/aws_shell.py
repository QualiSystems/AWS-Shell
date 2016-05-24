import jsonpickle

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.device_access_layer.aws_api import AWSApi
from cloudshell.cp.aws.domain.ami_managment.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.common.aws_session_manager import AWSSessionManager
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult


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
        :param aws_ami_deployment_model: The resource model of the AMI deployment option
        :type aws_ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param aws_ec2_resource_model: The resource model on which the AMI will be deployed on
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        """

        aws_ami_deployment_model, name = self._convert_to_deployment_resource_model(deployment_request)
        aws_ec2_resource_model = self.convert_to_aws_resource_model(command_context)

        access_key_id, secret_access_key = self.credentials_manager.get_credentials()
        ec2_session = self.aws_api.create_ec2_session(access_key_id, secret_access_key, aws_ec2_resource_model.region)
        result, name = self.deploy_ami_operation.deploy(ec2_session, name, aws_ec2_resource_model,
                                                        aws_ami_deployment_model)

        deploy_data = DeployResult(vm_name=name,
                                   vm_uuid=result.instance_id,
                                   cloud_provider_resource_name=aws_ami_deployment_model.aws_ec2,
                                   auto_power_on=aws_ami_deployment_model.auto_power_on,
                                   auto_power_off=aws_ami_deployment_model.auto_power_off,
                                   wait_for_ip=aws_ami_deployment_model.wait_for_ip,
                                   auto_delete=aws_ami_deployment_model.auto_delete,
                                   autoload=aws_ami_deployment_model.autoload)

        return self._set_command_result(deploy_data)

    def _set_command_result(self, result, unpicklable=False):
        """
        Serializes output as JSON and writes it to console output wrapped with special prefix and suffix
        :param result: Result to return
        :param unpicklable: If True adds JSON can be deserialized as real object.
                            When False will be deserialized as dictionary
        """
        json = jsonpickle.encode(result, unpicklable=unpicklable)
        result_for_output = str(json)
        print result_for_output
        return result_for_output

    def convert_to_aws_resource_model(self, command_context):
        resource_context = command_context.resource.attributes
        aws_ec2_resource_model = AWSEc2CloudProviderResourceModel()
        aws_ec2_resource_model.storage_size = resource_context['Storage Size']
        aws_ec2_resource_model.storage_iops = resource_context['Storage IOPS']
        aws_ec2_resource_model.region = self.get_region_code_from_name(resource_context['Region'])
        aws_ec2_resource_model.device_name = resource_context['Device Name']
        aws_ec2_resource_model.max_storage_iops = resource_context['Max Storage IOPS']
        aws_ec2_resource_model.max_storage_size = resource_context['Max Storage Size']
        return aws_ec2_resource_model

    def _convert_to_deployment_resource_model(self, deployment_request):
        data = jsonpickle.decode(deployment_request)
        data_holder = DeployDataHolder(data)
        deployment_resource_model = DeployAWSEc2AMIInstanceResourceModel()
        deployment_resource_model.aws_ec2 = data_holder.ami_params.aws_ec2
        deployment_resource_model.aws_ami_id = data_holder.ami_params.aws_ami_id
        deployment_resource_model.storage_size = data_holder.ami_params.storage_size
        deployment_resource_model.storage_iops = data_holder.ami_params.storage_iops
        deployment_resource_model.storage_type = data_holder.ami_params.storage_type
        deployment_resource_model.min_count = int(data_holder.ami_params.min_count)
        deployment_resource_model.max_count = int(data_holder.ami_params.max_count)
        deployment_resource_model.instance_type = data_holder.ami_params.instance_type
        deployment_resource_model.aws_key = data_holder.ami_params.aws_key
        deployment_resource_model.security_group_ids = data_holder.ami_params.security_group_ids
        deployment_resource_model.private_ip_address = data_holder.ami_params.private_ip_address
        deployment_resource_model.device_name = data_holder.ami_params.device_name
        deployment_resource_model.delete_on_termination = bool(data_holder.ami_params.delete_on_termination)
        deployment_resource_model.auto_power_on = bool(data_holder.ami_params.auto_power_on)
        deployment_resource_model.auto_power_off = bool(data_holder.ami_params.auto_power_off)
        deployment_resource_model.wait_for_ip = bool(data_holder.ami_params.wait_for_ip)
        deployment_resource_model.auto_delete = bool(data_holder.ami_params.auto_delete)
        deployment_resource_model.autoload = bool(data_holder.ami_params.autoload)
        deployment_resource_model.inbound_ports = data_holder.ami_params.inbound_ports
        deployment_resource_model.outbound_ports = data_holder.ami_params.outbound_ports
        return deployment_resource_model, data_holder.app_name

    def get_region_code_from_name(self, region):
        return "eu-central-1"

import jsonpickle

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class AWSModelsParser(object):
    @staticmethod
    def convert_app_resource_to_deployed_app(resource):
        json_str = jsonpickle.decode(resource.app_context.deployed_app_json)
        data_holder = DeployDataHolder(json_str)
        return data_holder

    @staticmethod
    def convert_to_aws_resource_model(resource):
        resource_context = resource.attributes
        aws_ec2_resource_model = AWSEc2CloudProviderResourceModel()
        aws_ec2_resource_model.region = resource_context['Region']
        aws_ec2_resource_model.max_storage_iops = resource_context['Max Storage IOPS']
        aws_ec2_resource_model.max_storage_size = resource_context['Max Storage Size']
        aws_ec2_resource_model.aws_secret_access_key = resource_context['AWS Secret Access Key']
        aws_ec2_resource_model.aws_access_key_id = resource_context['AWS Access Key ID']
        aws_ec2_resource_model.key_pairs_location = resource_context['Keypairs Location']
        aws_ec2_resource_model.aws_management_vpc_id = resource_context['AWS Management VPC ID']
        aws_ec2_resource_model.aws_management_sg_id = resource_context['AWS Management SG ID']
        aws_ec2_resource_model.instance_type = resource_context['Instance Type']

        return aws_ec2_resource_model

    @staticmethod
    def convert_to_deployment_resource_model(deployment_request):
        data = jsonpickle.decode(deployment_request)
        data_holder = DeployDataHolder(data)
        deployment_resource_model = DeployAWSEc2AMIInstanceResourceModel()
        deployment_resource_model.cloud_provider = data_holder.ami_params.cloud_provider
        deployment_resource_model.aws_ami_id = data_holder.ami_params.aws_ami_id
        deployment_resource_model.storage_size = data_holder.ami_params.storage_size
        deployment_resource_model.storage_iops = data_holder.ami_params.storage_iops
        deployment_resource_model.storage_type = data_holder.ami_params.storage_type
        deployment_resource_model.min_count = int(data_holder.ami_params.min_count)
        deployment_resource_model.max_count = int(data_holder.ami_params.max_count)
        deployment_resource_model.instance_type = data_holder.ami_params.instance_type
        deployment_resource_model.security_group_ids = data_holder.ami_params.security_group_ids
        deployment_resource_model.private_ip_address = data_holder.ami_params.private_ip_address
        deployment_resource_model.root_volume_name = data_holder.ami_params.root_volume_name
        deployment_resource_model.delete_on_termination = AWSModelsParser.convert_to_bool(data_holder.ami_params.delete_on_termination)
        deployment_resource_model.auto_power_off = \
            AWSModelsParser.convert_to_bool(data_holder.ami_params.auto_power_off)
        deployment_resource_model.wait_for_ip = AWSModelsParser.convert_to_bool(data_holder.ami_params.wait_for_ip)
        deployment_resource_model.auto_delete = AWSModelsParser.convert_to_bool(data_holder.ami_params.auto_delete)
        deployment_resource_model.autoload = AWSModelsParser.convert_to_bool(data_holder.ami_params.autoload)
        deployment_resource_model.inbound_ports = data_holder.ami_params.inbound_ports
        deployment_resource_model.outbound_ports = data_holder.ami_params.outbound_ports
        deployment_resource_model.wait_for_credentials = \
            AWSModelsParser.convert_to_bool(data_holder.ami_params.wait_for_credentials)
        deployment_resource_model.add_public_ip = AWSModelsParser.convert_to_bool(data_holder.ami_params.add_public_ip)
        deployment_resource_model.add_elastic_ip = data_holder.ami_params.add_elastic_ip
        return deployment_resource_model, data_holder.app_name

    @staticmethod
    def convert_to_bool(string):
        """
        Converts string to bool
        :param string: String
        :str string: str
        :return: True or False
        """
        if isinstance(string, bool):
            return string
        return string in ['true', 'True', '1']

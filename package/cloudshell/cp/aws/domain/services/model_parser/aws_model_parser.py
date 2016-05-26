import jsonpickle

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel

EC2_REGIONS = {'US East(N.Virginia)': 'us-east-1',
               'US West (N. California)': 'us-west-1',
               'US West (Oregon)': 'us-west-2',
               'EU (Ireland)': 'us-east-1',
               'EU (Frankfurt)': 'eu-central-1',
               'Asia Pacific (Tokyo)': 'ap-northeast-1',
               'Asia Pacific (Seoul)': 'ap-northeast-2',
               'Asia Pacific (Singapore)': 'ap-southeast-1',
               'Asia Pacific (Sydney)': 'ap-southeast-2',
               'South America (Sao Paulo)': '	sa-east-1'}


def convert_region(region):
    if region in EC2_REGIONS:
        return EC2_REGIONS[region]
    raise ValueError('EC2 region is not supported: {0}'.format(region))


def convert_to_aws_resource_model(command_context):
    resource_context = command_context.resource.attributes
    aws_ec2_resource_model = AWSEc2CloudProviderResourceModel()
    aws_ec2_resource_model.default_storage_size = resource_context['Default Storage Size']
    aws_ec2_resource_model.default_storage_iops = resource_context['Default Storage IOPS']
    aws_ec2_resource_model.region = convert_region(resource_context['Region'])
    aws_ec2_resource_model.device_name = resource_context['Device Name']
    aws_ec2_resource_model.max_storage_iops = resource_context['Max Storage IOPS']
    aws_ec2_resource_model.max_storage_size = resource_context['Max Storage Size']
    aws_ec2_resource_model.vpc = resource_context['VPC']
    aws_ec2_resource_model.aws_secret_access_key = resource_context['AWS Secret Access Key']
    aws_ec2_resource_model.aws_access_key_id = resource_context['AWS Access Key ID']
    aws_ec2_resource_model.default_instance_type = resource_context['Default Instance Type']
    aws_ec2_resource_model.subnet = resource_context['Subnet']
    return aws_ec2_resource_model


def convert_to_deployment_resource_model(deployment_request):
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

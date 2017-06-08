import jsonpickle

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.reservation_model import ReservationModel
from cloudshell.shell.core.driver_context import ReservationContextDetails


class AWSModelsParser(object):

    @staticmethod
    def convert_app_resource_to_deployed_app(resource):
        json_str = jsonpickle.decode(resource.app_context.deployed_app_json)
        data_holder = DeployDataHolder(json_str)
        return data_holder

    @staticmethod
    def convert_to_aws_resource_model(resource):
        """
        :rtype AWSEc2CloudProviderResourceModel:
        """
        resource_context = resource.attributes
        aws_ec2_resource_model = AWSEc2CloudProviderResourceModel()
        aws_ec2_resource_model.region = resource_context['Region']
        aws_ec2_resource_model.max_storage_iops = resource_context['Max Storage IOPS']
        aws_ec2_resource_model.max_storage_size = resource_context['Max Storage Size']
        aws_ec2_resource_model.aws_secret_access_key = resource_context['AWS Secret Access Key']
        aws_ec2_resource_model.aws_access_key_id = resource_context['AWS Access Key ID']
        aws_ec2_resource_model.key_pairs_location = resource_context['Keypairs Location']
        aws_ec2_resource_model.aws_management_vpc_id = resource_context['AWS Mgmt VPC ID']
        aws_ec2_resource_model.aws_management_sg_id = resource_context['AWS Mgmt SG ID']
        aws_ec2_resource_model.instance_type = resource_context['Instance Type']

        return aws_ec2_resource_model

    @staticmethod
    def convert_to_deployment_resource_model(deployment_request, resource_context_details):
        '''
        :type resource_context_details: ResourceContextDetails
        '''
        data = jsonpickle.decode(deployment_request)
        data_holder = DeployDataHolder(data)
        deployment_resource_model = DeployAWSEc2AMIInstanceResourceModel()
        deployment_resource_model.cloud_provider = resource_context_details.name
        deployment_resource_model.aws_ami_id = data["Attributes"]['AWS AMI Id']
        deployment_resource_model.storage_size = data["Attributes"]['Storage Size']
        deployment_resource_model.storage_iops = data["Attributes"]['Storage IOPS']
        deployment_resource_model.storage_type = data["Attributes"]['Storage Type']
        deployment_resource_model.instance_type = data["Attributes"]['Instance Type']
        deployment_resource_model.root_volume_name = data["Attributes"]['Root Volume Name']
        deployment_resource_model.wait_for_ip = AWSModelsParser.convert_to_bool(data["Attributes"]['Wait for IP'])
        deployment_resource_model.wait_for_status_check = AWSModelsParser.convert_to_bool(
            data["Attributes"]['Wait for Status Check'])
        deployment_resource_model.autoload = AWSModelsParser.convert_to_bool(data["Attributes"]['Autoload'])
        deployment_resource_model.inbound_ports = data["Attributes"]['Inbound Ports']
        deployment_resource_model.outbound_ports = data["Attributes"]['Outbound Ports']
        deployment_resource_model.wait_for_credentials = \
            AWSModelsParser.convert_to_bool(data["Attributes"]['Wait for Credentials'])
        deployment_resource_model.add_public_ip = AWSModelsParser.convert_to_bool(data["Attributes"]['Add Public IP'])
        deployment_resource_model.allocate_elastic_ip = \
            AWSModelsParser.convert_to_bool(data["Attributes"]['Allocate Elastic IP'])
        deployment_resource_model.user = data["LogicalResourceRequestAttributes"]["User"]
        deployment_resource_model.app_name = data_holder.AppName

        return deployment_resource_model

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

    @staticmethod
    def get_public_ip_from_connected_resource_details(resource_context):
        public_ip_on_resource = ""
        public_ip = 'Public IP'
        if resource_context.remote_endpoints is not None and public_ip in resource_context.remote_endpoints[
            0].attributes:
            public_ip_on_resource = resource_context.remote_endpoints[0].attributes[public_ip]
        return public_ip_on_resource

    @staticmethod
    def get_private_ip_from_connected_resource_details(resource_context):
        private_ip_on_resource = ""
        if resource_context.remote_endpoints is not None:
            private_ip_on_resource = resource_context.remote_endpoints[0].address
        return private_ip_on_resource

    @staticmethod
    def try_get_deployed_connected_resource_instance_id(resource_context):
        try:
            deployed_instance_id = str(
                jsonpickle.decode(resource_context.remote_endpoints[0].app_context.deployed_app_json)['vmdetails'][
                    'uid'])
        except Exception as e:
            raise ValueError('Could not find an ID of the AWS Deployed instance' + e.message)
        return deployed_instance_id

    @staticmethod
    def get_connectd_resource_fullname(resource_context):
        if resource_context.remote_endpoints[0]:
            return resource_context.remote_endpoints[0].fullname
        else:
            raise ValueError('Could not find resource fullname on the deployed app.')

    @staticmethod
    def convert_to_reservation_model(reservation_context):
        """
        :param ReservationContextDetails reservation_context:
        :rtype: ReservationModel
        """
        return ReservationModel(reservation_context)
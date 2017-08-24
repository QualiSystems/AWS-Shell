import re

import jsonpickle
from cloudshell.shell.core.driver_context import ReservationContextDetails

from cloudshell.cp.aws.common.converters import convert_to_bool
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.services.parsers.network_actions import NetworkActionsParser
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class AWSModelsParser(object):
    def __init__(self):
        pass

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
        aws_ec2_resource_model.reserved_ips_in_subnet = resource_context['Reserved IPs in Subnet']

        return aws_ec2_resource_model

    @staticmethod
    def convert_to_deployment_resource_model(deployment_request, resource):
        """
        :param str deployment_request: JSON string representing the deployment request
        :param ResourceContextDetails resource: The details of the resource using the driver
        """
        data = jsonpickle.decode(deployment_request)
        deployment_resource_model = DeployAWSEc2AMIInstanceResourceModel()

        deployment_resource_model.cloud_provider = resource.name
        deployment_resource_model.app_name = data["AppName"]

        deployment_resource_model.aws_ami_id = data["Attributes"]['AWS AMI Id']
        deployment_resource_model.storage_size = data["Attributes"]['Storage Size']
        deployment_resource_model.storage_iops = data["Attributes"]['Storage IOPS']
        deployment_resource_model.storage_type = data["Attributes"]['Storage Type']
        deployment_resource_model.instance_type = data["Attributes"]['Instance Type']
        deployment_resource_model.root_volume_name = data["Attributes"]['Root Volume Name']
        deployment_resource_model.wait_for_ip = convert_to_bool(data["Attributes"]['Wait for IP'])
        deployment_resource_model.wait_for_status_check = convert_to_bool(
                data["Attributes"]['Wait for Status Check'])
        deployment_resource_model.autoload = convert_to_bool(data["Attributes"]['Autoload'])
        deployment_resource_model.inbound_ports = data["Attributes"]['Inbound Ports']
        deployment_resource_model.wait_for_credentials = \
            convert_to_bool(data["Attributes"]['Wait for Credentials'])

        (deployment_resource_model.add_public_ip, deployment_resource_model.allocate_elastic_ip) = \
            AWSModelsParser.parse_public_ip_options_attribute(data["Attributes"]['Public IP Options'])

        deployment_resource_model.user = \
            AWSModelsParser.get_attribute_value_by_name_ignoring_namespace(
                    data["LogicalResourceRequestAttributes"], "User")

        deployment_resource_model.network_configurations = \
            AWSModelsParser.parse_deploy_networking_configurations(data)

        return deployment_resource_model

    @staticmethod
    def parse_public_ip_options_attribute(attr_value):
        """
        Parses the value of the "Public IP Options" attribute into a boolean tuple:
          (Add Public IP, Allocate Elastic IP)
        :param str attr_value: "Public IP Options" attribute value
        :return: Tuple of (Add Public IP, Allocate Elastic IP)
        :rtype: (boolean, boolean)
        """
        if re.match("^elastic", attr_value, flags=re.IGNORECASE):
            return False, True

        if re.match("^public ", attr_value, flags=re.IGNORECASE):
            return True, False

        return False, False

    @staticmethod
    def get_attribute_value_by_name_ignoring_namespace(attributes, name):
        """
        Finds the attribute value by name ignoring attribute namespaces.
        :param dict attributes: Attributes key value dict to search on.
        :param str name: Attribute name to search for.
        :return: Attribute str value. None if not found.
        :rtype: str
        """
        for key, val in attributes.iteritems():
            last_part = key.split(".")[-1]  # get last part of namespace.
            if name == last_part:
                return val
        return None

    @staticmethod
    def get_public_ip_from_connected_resource_details(resource_context):
        public_ip_on_resource = ""
        public_ip = 'Public IP'
        if resource_context.remote_endpoints is not None:
            public_ip_on_resource = AWSModelsParser.get_attribute_value_by_name_ignoring_namespace(
                    resource_context.remote_endpoints[0].attributes, public_ip)
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

    @staticmethod
    def parse_deploy_networking_configurations(deployment_request):
        """
        :param deployment_request: request object to parse
        :return:
        """
        if "NetworkConfigurationsRequest" not in deployment_request:
            return None

        actions = deployment_request["NetworkConfigurationsRequest"]["actions"]

        return NetworkActionsParser.parse_network_actions_data(actions)

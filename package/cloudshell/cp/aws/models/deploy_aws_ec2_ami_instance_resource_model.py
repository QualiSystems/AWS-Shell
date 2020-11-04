import json

from typing import Dict, List
from cloudshell.cp.core.requested_ips.parser import RequestedIPsParser
from cloudshell.cp.aws.common.converters import convert_to_bool
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser


class DeployAWSEc2AMIInstanceResourceModel(object):
    __deploymentModel__ = "AWS EC2 Instance"

    def __init__(self, attributes):  # todo handle the c=initialization of the object from the attributes
        self.user_data_url = ''
        self.user_data_run_parameters = ''

        self.custom_tags = ''
        self.cloud_provider = ''
        self.aws_ami_id = ''
        self.storage_size = ''
        self.storage_iops = ''
        # the storage type can be one of these: 'standard'|'io1'|'gp2'|'sc1'|'st1'
        self.storage_type = ''  # type: str
        self.min_count = 0  # type: int
        self.max_count = 0  # type: int
        self.instance_type = ''  # type: str
        self.iam_role = ''  # type: str
        self.security_group_ids = None  # type: str
        self.private_ip_address = ""  # type: str
        self.private_ip_addresses_list = None  # type: Dict
        self.root_volume_name = ''  # type: str
        self.delete_on_termination = True  # type: bool
        self.auto_power_off = False  # type: bool
        self.wait_for_ip = False  # type: bool
        self.wait_for_status_check = False  # type: bool
        self.auto_delete = False  # type: bool
        self.autoload = False  # type: bool
        self.outbound_ports = ''  # type: str
        self.inbound_ports = ''  # type: str
        self.wait_for_credentials = ''  # type: str
        self.add_public_ip = False  # type: bool
        self.allocate_elastic_ip = False  # type: bool
        self.network_configurations = None  # type: list[NetworkAction]
        self.allow_all_sandbox_traffic = True  # type: bool

        self.aws_ami_id = attributes["AWS AMI Id"]
        self.allow_all_sandbox_traffic = convert_to_bool(attributes['Allow all Sandbox Traffic'])
        self.storage_size = attributes['Storage Size']
        self.storage_iops = attributes['Storage IOPS']
        self.storage_type = attributes['Storage Type']
        self.instance_type = attributes['Instance Type']
        self.iam_role = attributes['IAM Role Name']
        self.root_volume_name = attributes['Root Volume Name']
        self.wait_for_ip = convert_to_bool(attributes['Wait for IP'])
        self.wait_for_status_check = convert_to_bool(attributes['Wait for Status Check'])
        self.autoload = convert_to_bool(attributes['Autoload'])
        self.inbound_ports = attributes['Inbound Ports']
        self.wait_for_credentials = convert_to_bool(attributes['Wait for Credentials'])
        (self.add_public_ip, self.allocate_elastic_ip) = \
            AWSModelsParser.parse_public_ip_options_attribute(attributes['Public IP Options'])
        self.custom_tags = attributes['Custom Tags']
        self.user_data_url = attributes['User Data URL']
        self.user_data_run_parameters = attributes['User Data Parameters']

        self.private_ip_addresses_list = self._get_private_ip_addresses(attributes)
        self.private_ip_address = self._get_primary_private_ip_address(self.private_ip_addresses_list)

    def _get_private_ip_addresses(self, attributes):
        """
        :param dict attributes:
        :rtype: List[List[str]]
        """
        if attributes:
            return RequestedIPsParser.parse(attributes)
        return None

    def _get_primary_private_ip_address(self, private_ip_addresses_list):
        """
        :param List[List[str]] private_ip_addresses_list:
        :rtype: str
        """
        if private_ip_addresses_list:
            return private_ip_addresses_list[0][0]
        return None

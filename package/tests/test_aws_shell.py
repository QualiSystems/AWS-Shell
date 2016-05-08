
from unittest import TestCase

from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class TestAWSShell(TestCase):
    def setUp(self):
        self.aws_sell_api = AWSShell()

    def test_aws_deploy_ami(self):
        aws_ec2_cp = AWSEc2CloudProviderResourceModel()
        aws_ec2_cp.instance_type = 't2.nano'
        aws_ec2_cp.aws_key = 'aws_testing_key_pair'
        aws_ec2_cp.min_count = 1
        aws_ec2_cp.max_count = 1

        # Block device mappings settings
        aws_ec2_cp.device_name = '/dev/sda1'
        aws_ec2_cp.storage_size = 30
        aws_ec2_cp.delete_on_termination = True
        aws_ec2_cp.storage_type = 'gp2'
        aws_ec2_cp.security_group_ids = 'sg-66ea1b0e'

        ami_model = DeployAWSEc2AMIInstanceResourceModel()
        ami_model.aws_ami_id = 'ami-3acf2f55'

        self.aws_sell_api.deploy_ami(aws_ec2_cp, ami_model)



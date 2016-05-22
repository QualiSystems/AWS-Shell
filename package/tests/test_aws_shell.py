from unittest import TestCase

import jsonpickle
from mock import Mock, MagicMock
from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class TestAWSShell(TestCase):
    def setUp(self):
        self.aws_shell_api = AWSShell()

    def test_deploying_ami_returns_deploy_result(self):
        name = 'my instance name'
        result = Mock()
        result.instance_id = 'my instance id'

        self.aws_shell_api._convert_to_deployment_resource_model = \
            Mock(return_value=((DeployAWSEc2AMIInstanceResourceModel()), name))
        self.aws_shell_api.convert_to_aws_resource_model = \
            Mock(return_value=(AWSEc2CloudProviderResourceModel()))

        self.aws_shell_api.aws_api.create_ec2_session = Mock(return_value=Mock())
        self.aws_shell_api.deploy_ami_operation.deploy = Mock(return_value=(result, name))

        deploy = DeployAWSEc2AMIInstanceResourceModel()
        aws_cloud_provider = AWSEc2CloudProviderResourceModel()
        res = self.aws_shell_api.deploy_ami(deploy, aws_cloud_provider)

        ami_res_name = jsonpickle.decode(res)['vm_name']
        instance_id = jsonpickle.decode(res)['vm_uuid']

        self.assertEqual(ami_res_name, name)
        self.assertEqual(instance_id, result.instance_id)

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

        self.aws_shell_api.deploy_ami(aws_ec2_cp, ami_model)

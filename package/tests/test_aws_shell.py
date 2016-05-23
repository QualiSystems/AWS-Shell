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

        deploymock = DeployAWSEc2AMIInstanceResourceModel()
        deploymock.auto_power_on = "True"
        deploymock.auto_power_off = "True"
        deploymock.wait_for_ip = "True"
        deploymock.auto_delete = "True"
        deploymock.autoload = "True"
        deploymock.aws_ec2 = "some_name"

        self.aws_shell_api._convert_to_deployment_resource_model = \
            Mock(return_value=(deploymock, name))
        self.aws_shell_api.convert_to_aws_resource_model = \
            Mock(return_value=(AWSEc2CloudProviderResourceModel()))

        self.aws_shell_api.aws_api.create_ec2_session = Mock(return_value=Mock())
        self.aws_shell_api.deploy_ami_operation.deploy = Mock(return_value=(result, name))

        aws_cloud_provider = AWSEc2CloudProviderResourceModel()
        res = self.aws_shell_api.deploy_ami(deploymock, aws_cloud_provider)

        ami_res_name = jsonpickle.decode(res)['vm_name']
        instance_id = jsonpickle.decode(res)['vm_uuid']

        self.assertEqual(ami_res_name, name)
        self.assertEqual(instance_id, result.instance_id)
        self.assertEqual(instance_id, result.instance_id)
        self.assertEqual(jsonpickle.decode(res)['auto_power_on'], deploymock.auto_power_on)
        self.assertEqual(jsonpickle.decode(res)['auto_power_off'], deploymock.auto_power_off)
        self.assertEqual(jsonpickle.decode(res)['wait_for_ip'], deploymock.wait_for_ip)
        self.assertEqual(jsonpickle.decode(res)['auto_delete'], deploymock.auto_delete)
        self.assertEqual(jsonpickle.decode(res)['autoload'], deploymock.autoload)
        self.assertEqual(jsonpickle.decode(res)['cloud_provider_resource_name'],deploymock.aws_ec2)

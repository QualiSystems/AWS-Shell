from unittest import TestCase

from cloudshell.cp.core import DriverRequestParser
from cloudshell.cp.core.models import PrepareSubnetParams, PrepareCloudInfra, ConnectToSubnetParams
from mock import Mock

from cloudshell.cp.aws.common.converters import convert_to_bool
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class TestModelParser(TestCase):
    def setUp(self):
        pass

    def test_parse_public_ip_options_attribute_elastic(self):
        # arrange
        public_ip_options_val = "Elastic IPs"

        # act
        (public, elastic) = AWSModelsParser.parse_public_ip_options_attribute(public_ip_options_val)

        # assert
        self.assertFalse(public)
        self.assertTrue(elastic)

    def test_parse_public_ip_options_attribute_public(self):
        # arrange
        public_ip_options_val = "Public IP"

        # act
        (public, elastic) = AWSModelsParser.parse_public_ip_options_attribute(public_ip_options_val)

        # assert
        self.assertTrue(public)
        self.assertFalse(elastic)

    def test_parse_public_ip_options_attribute_no_public_ip(self):
        # arrange
        public_ip_options_val = "No Public IP"

        # act
        (public, elastic) = AWSModelsParser.parse_public_ip_options_attribute(public_ip_options_val)

        # assert
        self.assertFalse(public)
        self.assertFalse(elastic)

    def test_convert_to_deployment_resource_model(self):
        # Arrange
        json = '{'\
                  '"driverRequest": {'\
                    '"actions": ['\
                      '{'\
                        '"actionParams": {'\
                          '"appName": "AWS",'\
                          '"deployment": {'\
                            '"deploymentPath": "AWS EC2 Instance",'\
                            '"attributes": ['\
                              '{'\
                                '"attributeName": "AWS AMI Id",'\
                                '"attributeValue": "ami_id",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Custom Tags",'\
                                '"attributeValue": "custom_tags",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "User Data URL",'\
                                '"attributeValue": "user_data_url",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "User Data Parameters",'\
                                '"attributeValue": "user_data_parameters",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Allow all Sandbox Traffic",'\
                                '"attributeValue": "True",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Instance Type",'\
                                '"attributeValue": "t.nano",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Storage Size",'\
                                '"attributeValue": "0",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Storage IOPS",'\
                                '"attributeValue": "0",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Storage Type",'\
                                '"attributeValue": "storage_type",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Inbound Ports",'\
                                '"attributeValue": "80",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Wait for IP",'\
                                '"attributeValue": "False",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Wait for Status Check",'\
                                '"attributeValue": "True",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Autoload",'\
                                '"attributeValue": "False",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Wait for Credentials",'\
                                '"attributeValue": "False",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Public IP Options",'\
                                '"attributeValue": "Elastic IP",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Root Volume Name",'\
                                '"attributeValue": "root_vol_name",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "IAM Role Name",'\
                                '"attributeValue": "top secret",'\
                                '"type": "attribute"'\
                              '},' \
                              '{' \
                                '"attributeName": "Private IP",' \
                                '"attributeValue": "",' \
                                '"type": "attribute"' \
                              '}' \
                            '],'\
                            '"type": "deployAppDeploymentInfo"'\
                          '},'\
                          '"appResource": {'\
                            '"attributes": ['\
                              '{'\
                                '"attributeName": "Password",'\
                                '"attributeValue": "3M3u7nkDzxWb0aJ/IZYeWw==",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Public IP",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "User",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '}'\
                            '],'\
                            '"type": "appResourceInfo"'\
                          '},'\
                          '"type": "deployAppParams"'\
                        '},'\
                        '"actionId": "f09b5640-1349-440d-b66f-f16a3009369f",'\
                        '"type": "deployApp"'\
                      '}'\
                    ']'\
                  '}'\
                '}'

        # Act
        self.request_parser = DriverRequestParser()
        self.request_parser.add_deployment_model(deployment_model_cls=DeployAWSEc2AMIInstanceResourceModel)
        model = self.request_parser.convert_driver_request_to_actions(json)[0]

        # Assert
        self.assertEquals(model.actionParams.deployment.customModel.aws_ami_id, "ami_id")
        self.assertEquals(model.actionParams.deployment.customModel.storage_size, "0")
        self.assertEquals(model.actionParams.deployment.customModel.storage_iops, "0")
        self.assertEquals(model.actionParams.deployment.customModel.storage_type, "storage_type")
        self.assertEquals(model.actionParams.deployment.customModel.instance_type, "t.nano")
        self.assertEquals(model.actionParams.deployment.customModel.iam_role, "top secret")
        self.assertEquals(model.actionParams.deployment.customModel.root_volume_name, "root_vol_name")
        self.assertFalse(model.actionParams.deployment.customModel.wait_for_ip)
        self.assertTrue(model.actionParams.deployment.customModel.wait_for_status_check)
        self.assertFalse(model.actionParams.deployment.customModel.autoload)
        self.assertEquals(model.actionParams.deployment.customModel.inbound_ports, "80")
        self.assertFalse(model.actionParams.deployment.customModel.wait_for_credentials)
        self.assertFalse(model.actionParams.deployment.customModel.add_public_ip)
        self.assertTrue(model.actionParams.deployment.customModel.allocate_elastic_ip)

    def test_convert_to_deployment_resource_model_with_network(self):
        json = '{'\
                  '"driverRequest": {'\
                    '"actions": ['\
                      '{'\
                        '"actionParams": {'\
                          '"cidr": "10.0.5.0/28",'\
                          '"subnetId": "some_id",'\
                          '"isPublic": true,'\
                          '"subnetServiceAttributes": ['\
                            '{'\
                              '"attributeName": "QnQ",'\
                              '"attributeValue": "False",'\
                              '"type": "attribute"'\
                            '},'\
                            '{'\
                              '"attributeName": "CTag",'\
                              '"attributeValue": "",'\
                              '"type": "attribute"'\
                            '},'\
                            '{'\
                              '"attributeName": "Subnet Size",'\
                              '"attributeValue": "16",'\
                              '"type": "attribute"'\
                            '},'\
                            '{'\
                              '"attributeName": "Public",'\
                              '"attributeValue": "True",'\
                              '"type": "attribute"'\
                            '},'\
                            '{'\
                              '"attributeName": "Allocated CIDR",'\
                              '"attributeValue": "10.0.1.0/28",'\
                              '"type": "attribute"'\
                            '},'\
                            '{'\
                              '"attributeName": "Subnet Id",'\
                              '"attributeValue": "some_id",'\
                              '"type": "attribute"'\
                            '}'\
                          '],'\
                          '"type": "connectToSubnetParams"'\
                        '},'\
                        '"actionId": "some_id",'\
                        '"type": "connectSubnet"'\
                      '},'\
                      '{'\
                        '"actionParams": {'\
                          '"appName": "AWS",'\
                          '"deployment": {'\
                            '"deploymentPath": "AWS EC2 Instance",'\
                            '"attributes": ['\
                              '{'\
                                '"attributeName": "AWS AMI Id",'\
                                '"attributeValue": "ami-b7b4fedd",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Allow all Sandbox Traffic",'\
                                '"attributeValue": "True",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Wait for IP",'\
                                '"attributeValue": "False",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Wait for Status Check",'\
                                '"attributeValue": "False",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Autoload",'\
                                '"attributeValue": "True",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Wait for Credentials",'\
                                '"attributeValue": "True",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Public IP Options",'\
                                '"attributeValue": "No Public IP",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Root Volume Name",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "IAM Role Name",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Instance Type",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Storage Size",'\
                                '"attributeValue": "0",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Storage IOPS",'\
                                '"attributeValue": "0",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Storage Type",'\
                                '"attributeValue": "auto",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Inbound Ports",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '}'\
                            '],'\
                            '"type": "deployAppDeploymentInfo"'\
                          '},'\
                          '"appResource": {'\
                            '"attributes": ['\
                              '{'\
                                '"attributeName": "Password",'\
                                '"attributeValue": "3M3u7nkDzxWb0aJ/IZYeWw==",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "Public IP",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '},'\
                              '{'\
                                '"attributeName": "User",'\
                                '"attributeValue": "",'\
                                '"type": "attribute"'\
                              '}'\
                            '],'\
                            '"type": "appResourceInfo"'\
                          '},'\
                          '"type": "deployAppParams"'\
                        '},'\
                        '"actionId": "bbf48f30-1e75-45b0-b49a-23c5d0213727",'\
                        '"type": "deployApp"'\
                      '}'\
                    ']'\
                  '}'\
                '}'
        resource = Mock()
        resource.name = "cloud_provider_name"

        # Act
        self.request_parser = DriverRequestParser()
        self.request_parser.add_deployment_model(deployment_model_cls=DeployAWSEc2AMIInstanceResourceModel)
        model = self.request_parser.convert_driver_request_to_actions(json)[0]

        # Assert
        self.assertEquals(model.actionId, "some_id")
        self.assertEquals(len(model.actionParams.subnetServiceAttributes), 6)
        self.assertEquals(model.actionParams.subnetServiceAttributes["Public"], 'True')
        self.assertTrue(isinstance(model.actionParams, ConnectToSubnetParams))

    def test_subnet_connection_params_check_is_public_subnet_true(self):
        # arrange
        test_obj = PrepareSubnetParams()
        attr1 = PrepareCloudInfra()
        attr1.name = "Some Attribute"
        attr1.value = "Some Value"
        attr2 = PrepareCloudInfra()
        attr2.name = "Public"
        attr2.value = "True"
        test_obj.subnetServiceAttributes = [attr1, attr2]

        # act
        is_public = test_obj.isPublic

        # assert
        self.assertTrue(is_public)

    def test_subnet_connection_params_check_is_public_subnet_true_when_no_attribute(self):
        # arrange
        test_obj = PrepareSubnetParams()
        attr1 = PrepareCloudInfra()
        attr1.name = "Some Attribute"
        attr1.value = "Some Value"
        test_obj.subnetServiceAttributes = [attr1]

        # act
        is_public = test_obj.isPublic

        # assert
        self.assertTrue(is_public)

    def test_parse_bool_value_as_string_and_as_boolean(self):
        self.assertTrue(convert_to_bool("True"))
        self.assertTrue(convert_to_bool(True))
        self.assertFalse(convert_to_bool("False"))
        self.assertFalse(convert_to_bool(False))
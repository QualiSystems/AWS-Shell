from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.common.converters import convert_to_bool
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.models.network_actions_models import SubnetConnectionParams, NetworkActionAttribute


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
        request = '{' \
                    '"Attributes": {' \
                          '"AWS AMI Id":"ami_id",' \
                          '"Storage Size": "0",' \
                          '"Storage IOPS":"0",' \
                          '"Storage Type":"storage_type",' \
                          '"Instance Type":"t.nano",' \
                          '"IAM Role Name":"top secret",'\
                          '"Root Volume Name":"root_vol_name",' \
                          '"Wait for IP":"False",' \
                          '"Wait for Status Check":"True",' \
                          '"Autoload":"False",' \
                          '"Inbound Ports":"80",' \
                          '"Wait for Credentials":"False",' \
                          '"Public IP Options":"Elastic IP",' \
                          '"Allow all Sandbox Traffic": "True"' \
                        '},' \
                    '"LogicalResourceRequestAttributes": {"User": "some_user"},' \
                    '"AppName": "my_app"' \
                  '}'
        resource = Mock()
        resource.name = "cloud_provider_name"

        # Act
        model = AWSModelsParser.convert_to_deployment_resource_model(deployment_request=request, resource=resource)

        # Assert
        self.assertEquals(model.cloud_provider, "cloud_provider_name")
        self.assertEquals(model.aws_ami_id, "ami_id")
        self.assertEquals(model.storage_size, "0")
        self.assertEquals(model.storage_iops, "0")
        self.assertEquals(model.storage_type, "storage_type")
        self.assertEquals(model.instance_type, "t.nano")
        self.assertEquals(model.iam_role, "top secret")
        self.assertEquals(model.root_volume_name, "root_vol_name")
        self.assertFalse(model.wait_for_ip)
        self.assertTrue(model.wait_for_status_check)
        self.assertFalse(model.autoload)
        self.assertEquals(model.inbound_ports, "80")
        self.assertFalse(model.wait_for_credentials)
        self.assertFalse(model.add_public_ip)
        self.assertTrue(model.allocate_elastic_ip)
        self.assertEquals(model.user, "some_user")
        self.assertEquals(model.app_name, "my_app")
        self.assertIsNone(model.network_configurations)

    def test_convert_to_deployment_resource_model_with_network(self):
        request = '{' \
                    '"Attributes": {' \
                          '"AWS AMI Id":"ami_id",' \
                          '"Storage Size": "0",' \
                          '"Storage IOPS":"0",' \
                          '"Storage Type":"storage_type",' \
                          '"Instance Type":"t.nano",' \
                          '"IAM Role Name":"top secret",'\
                          '"Root Volume Name":"root_vol_name",' \
                          '"Wait for IP":"False",' \
                          '"Wait for Status Check":"True",' \
                          '"Autoload":"False",' \
                          '"Inbound Ports":"80",' \
                          '"Wait for Credentials":"False",' \
                          '"Public IP Options":"Elastic IP",' \
                          '"Allow all Sandbox Traffic": "True"' \
                        '},' \
                    '"LogicalResourceRequestAttributes": {"User": "some_user"},' \
                    '"AppName": "my_app",' \
                    '"NetworkConfigurationsRequest": { ' \
                        '"actions": [' \
                        '{' \
                            '"actionId": "some_id",' \
                            '"type": "connectToSubnet",' \
                            '"connectionParams": {' \
                                '"type": "connectToSubnetParams",' \
                                '"cidr": "10.0.5.0/28",' \
                                '"subnetId": "some_id",' \
                                '"subnetServiceAttributes": [' \
                                    '{' \
                                        '"type": "subnetServiceAttribute",' \
                                        '"attributeName": "aaa",' \
                                        '"attributeValue": "aaa"' \
                                    '},{' \
                                        '"type": "subnetServiceAttribute",' \
                                        '"attributeName": "bbb",' \
                                        '"attributeValue": "bbb"' \
                                '}]' \
                            '},' \
                            '"customActionAttributes": [{' \
                                '"attributeName": "Vnic Name",' \
                                '"attributeValue": "0"' \
                            '}]' \
                        '}' \
                    ']}' \
                  '}'
        resource = Mock()
        resource.name = "cloud_provider_name"

        # Act
        model = AWSModelsParser.convert_to_deployment_resource_model(deployment_request=request, resource=resource)

        # Assert
        self.assertEquals(len(model.network_configurations), 1)
        self.assertEquals(model.network_configurations[0].id, "some_id")
        self.assertEquals(model.network_configurations[0].type, "connectToSubnet")
        self.assertEquals(len(model.network_configurations[0].connection_params.custom_attributes), 1)
        self.assertEquals(model.network_configurations[0].connection_params.custom_attributes[0].name, "Vnic Name")
        self.assertEquals(model.network_configurations[0].connection_params.custom_attributes[0].value, "0")
        self.assertTrue(isinstance(model.network_configurations[0].connection_params, SubnetConnectionParams))

    def test_subnet_connection_params_check_is_public_subnet_true(self):
        # arrange
        test_obj = SubnetConnectionParams()
        attr1 = NetworkActionAttribute()
        attr1.name = "Some Attribute"
        attr1.value = "Some Value"
        attr2 = NetworkActionAttribute()
        attr2.name = "Public"
        attr2.value = "True"
        test_obj.subnetServiceAttributes = [attr1, attr2]

        # act
        is_public = test_obj.is_public_subnet()

        # assert
        self.assertTrue(is_public)

    def test_subnet_connection_params_check_is_public_subnet_false(self):
        # arrange
        test_obj = SubnetConnectionParams()
        attr1 = NetworkActionAttribute()
        attr1.name = "Some Attribute"
        attr1.value = "Some Value"
        attr2 = NetworkActionAttribute()
        attr2.name = "Public"
        attr2.value = "False"
        test_obj.subnetServiceAttributes = [attr1, attr2]

        # act
        is_public = test_obj.is_public_subnet()

        # assert
        self.assertFalse(is_public)

    def test_subnet_connection_params_check_is_public_subnet_true_when_no_attribute(self):
        # arrange
        test_obj = SubnetConnectionParams()
        attr1 = NetworkActionAttribute()
        attr1.name = "Some Attribute"
        attr1.value = "Some Value"
        test_obj.subnetServiceAttributes = [attr1]

        # act
        is_public = test_obj.is_public_subnet()

        # assert
        self.assertTrue(is_public)

    def test_parse_bool_value_as_string_and_as_boolean(self):
        self.assertTrue(convert_to_bool("True"))
        self.assertTrue(convert_to_bool(True))
        self.assertFalse(convert_to_bool("False"))
        self.assertFalse(convert_to_bool(False))
from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation


class TestDeployOperation(TestCase):
    def setUp(self):
        self.ec2_datamodel = Mock()
        self.ec2_datamodel.default_storage_size = 1
        self.ec2_session = Mock()
        self.s3_session = Mock()
        self.ec2_serv = Mock()
        self.security_group_service = Mock()
        self.tag_service = Mock()
        self.key_pair = Mock()
        self.vpc_service = Mock()
        self.subnet_service = Mock()
        self.credentials_manager = Mock()
        self.deploy_operation = DeployAMIOperation(self.ec2_serv,
                                                   self.credentials_manager,
                                                   self.security_group_service,
                                                   self.tag_service,
                                                   self.vpc_service,
                                                   self.key_pair,
                                                   self.subnet_service)

    def test_deploy(self):
        ami_datamodel = Mock()
        ami_datamodel.storage_size = None
        ami_datamodel.inbound_ports = "80"
        ami_datamodel.outbound_ports = None
        ami_datamodel.add_public_ip = None
        ami_datamodel.add_elastic_ip = None
        instance = Mock()
        instance.tags = [{'Key': 'Name', 'Value': 'my name'}]
        self.ec2_serv.create_instance = Mock(return_value=instance)
        res = self.deploy_operation.deploy(self.ec2_session,
                                           self.s3_session,
                                           'my name',
                                           'reservation_id',
                                           self.ec2_datamodel,
                                           ami_datamodel)
        ami_credentials = self.credentials_manager.get_windows_credentials()

        self.assertEqual(res.vm_name, 'my name')
        self.assertEqual(res.cloud_provider_resource_name, ami_datamodel.cloud_provider_resource)
        self.assertEqual(res.auto_power_on, ami_datamodel.auto_power_on)
        self.assertEqual(res.auto_power_off, ami_datamodel.auto_power_off)
        self.assertEqual(res.wait_for_ip, ami_datamodel.wait_for_ip)
        self.assertEqual(res.auto_delete, ami_datamodel.auto_delete)
        self.assertEqual(res.autoload, ami_datamodel.autoload)
        self.assertEqual(res.inbound_ports, ami_datamodel.inbound_ports)
        self.assertEqual(res.outbound_ports, ami_datamodel.outbound_ports)
        self.assertEqual(res.vm_uuid, instance.instance_id)
        self.assertEqual(res.deployed_app_attributes, {'Password': ami_credentials.password,
                                                       'User': ami_credentials.user_name})
        self.assertTrue(self.tag_service.get_security_group_tags.called)
        self.assertTrue(self.security_group_service.create_security_group.called)
        self.assertTrue(self.ec2_serv.set_ec2_resource_tags.called_with(
            self.security_group_service.create_security_group()),
            self.tag_service.get_security_group_tags())

        self.assertTrue(self.key_pair.load.called_with(self.ec2_datamodel.key_pair_location,
                                                       instance.key_pair.key_name,
                                                       self.key_pair.FILE_SYSTEM))

        self.assertTrue(self.security_group_service.set_security_group_rules.called_with(
            ami_datamodel, self.security_group_service.create_security_group()))

    def test_get_block_device_mappings_not_defaults(self):
        ami = Mock()
        ami.device_name = 'name'
        ami.storage_size = '0'
        ami.delete_on_termination = True
        ami.storage_type = 'type'
        res = self.deploy_operation._get_block_device_mappings(ami, Mock())
        self.assertEqual(res[0]['DeviceName'], ami.device_name)
        self.assertEqual(str(res[0]['Ebs']['VolumeSize']), ami.storage_size)
        self.assertEqual(res[0]['Ebs']['DeleteOnTermination'], ami.delete_on_termination)
        self.assertEqual(res[0]['Ebs']['VolumeType'], ami.storage_type)

    def test_get_block_device_mappings_defaults(self):
        ec_model = Mock()
        ec_model.device_name = 'name'
        ec_model.default_storage_size = '0'
        ec_model.delete_on_termination = True
        ec_model.default_storage_type = 'type'
        ami = Mock()
        ami.device_name = ''
        ami.storage_size = ''
        ami.delete_on_termination = None
        ami.storage_type = ''
        res = self.deploy_operation._get_block_device_mappings(ami, ec_model)
        self.assertEqual(res[0]['DeviceName'], ec_model.device_name)
        self.assertEqual(str(res[0]['Ebs']['VolumeSize']), ec_model.default_storage_size)
        self.assertEqual(res[0]['Ebs']['DeleteOnTermination'], ec_model.delete_on_termination)
        self.assertEqual(res[0]['Ebs']['VolumeType'], ec_model.default_storage_type)

    def test_create_deployment_parameters_no_ami_id(self):
        ami = Mock()
        ami.aws_ami_id = None
        self.assertRaises(ValueError,
                          self.deploy_operation._create_deployment_parameters,
                          aws_ec2_resource_model=self.ec2_datamodel,
                          ami_deployment_model=ami,
                          vpc=Mock(),
                          security_group=None,
                          key_pair='keypair',
                          reservation_id='res')

    def test_create_deployment_parameters(self):
        ami = Mock()
        ami.aws_ami_id = 'asd'
        ami.storage_size = '0'
        vpc = Mock()
        aws_model = self.deploy_operation._create_deployment_parameters(aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation_id='res')

        self.assertEquals(aws_model.min_count, 1)
        self.assertEquals(aws_model.max_count, 1)
        self.assertEquals(aws_model.aws_key, 'keypair')
        self.assertTrue(len(aws_model.security_group_ids) == 1)
        return aws_model

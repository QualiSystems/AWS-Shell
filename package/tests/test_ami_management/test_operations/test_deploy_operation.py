from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation


class TestDeployOperation(TestCase):
    def setUp(self):
        self.ec2_datamodel = Mock()
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
        ami_datamodel.storage_size = 30
        ami_datamodel.inbound_ports = "80"
        ami_datamodel.outbound_ports = "20"
        ami_datamodel.add_public_ip = None
        ami_datamodel.add_elastic_ip = None
        instance = Mock()
        instance.tags = [{'Key': 'Name', 'Value': 'my name'}]
        self.ec2_serv.create_instance = Mock(return_value=instance)
        sg = Mock()
        self.security_group_service.create_security_group = Mock(return_value=sg)
        self.deploy_operation._get_block_device_mappings = Mock()

        # act
        res = self.deploy_operation.deploy(self.ec2_session,
                                           self.s3_session,
                                           'my name',
                                           Mock(),
                                           self.ec2_datamodel,
                                           ami_datamodel)
        ami_credentials = self.credentials_manager.get_windows_credentials()

        # assert
        self.assertEqual(res.vm_name, 'my name')
        self.assertEqual(res.cloud_provider_resource_name, ami_datamodel.cloud_provider)
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

        self.security_group_service.remove_allow_all_outbound_rule.assert_called_with(security_group=sg)

    def test_get_block_device_mappings_throws_max_storage_error(self):
        ec_model = Mock()
        ec_model.max_storage_size = 30
        ec_model.max_storage_iops = 0

        ami = Mock()
        ami.root_volume_name = 'name'
        ami.storage_size = 50
        ami.storage_iops = 0
        ami.storage_type = ''

        image = Mock()
        image.root_device_name = '/sda'
        root_device = {'DeviceName': image.root_device_name,
                       'Ebs': {}}
        image.block_device_mappings = [root_device]

        with self.assertRaisesRegexp(ValueError, 'Requested storage size is bigger than the max allowed storage size of 30'):
            self.deploy_operation._get_block_device_mappings(image=image,
                                                             ami_deployment_model=ami,
                                                             aws_ec2_resource_model=ec_model)

    def test_get_block_device_mappings_throws_max_iops_error(self):
        ec_model = Mock()
        ec_model.max_storage_size = 30
        ec_model.max_storage_iops = 100

        ami = Mock()
        ami.root_volume_name = 'name'
        ami.storage_size = 30
        ami.storage_iops = 200
        ami.storage_type = 'io1'

        image = Mock()
        image.root_device_name = '/sda'
        root_device = {'DeviceName': image.root_device_name,
                       'Ebs': {}}
        image.block_device_mappings = [root_device]

        with self.assertRaisesRegexp(ValueError, 'Requested storage IOPS is bigger than the max allowed storage IOPS of 100'):
            self.deploy_operation._get_block_device_mappings(image=image,
                                                             ami_deployment_model=ami,
                                                             aws_ec2_resource_model=ec_model)

    def test_get_block_device_mappings_from_image(self):
        ec_model = Mock()
        ec_model.max_storage_size = 0
        ec_model.max_storage_iops = 0

        ami = Mock()
        ami.root_volume_name = 'name'
        ami.storage_size = 0
        ami.storage_iops = 0
        ami.storage_type = ''

        image = Mock()
        image.root_device_name = '/sda'
        root_device = {'DeviceName': image.root_device_name,
                       'Ebs': {
                           'VolumeSize': '40',
                           'VolumeType': 'io1',
                           'Iops': '240'
                       }}
        image.block_device_mappings = [root_device]

        res = self.deploy_operation._get_block_device_mappings(image=image,
                                                               ami_deployment_model=ami,
                                                               aws_ec2_resource_model=ec_model)

        self.assertEqual(res[0]['DeviceName'], ami.root_volume_name)
        self.assertEqual(str(res[0]['Ebs']['VolumeSize']), str(40))
        self.assertEqual(res[0]['Ebs']['DeleteOnTermination'], True)
        self.assertEqual(res[0]['Ebs']['VolumeType'], 'io1')
        self.assertEqual(res[0]['Ebs']['Iops'], 240)

    def test_get_block_device_mappings_from_ami(self):
        ec_model = Mock()
        ec_model.max_storage_size = 0
        ec_model.max_storage_iops = 0

        ami = Mock()
        ami.root_volume_name = 'name'
        ami.storage_size = 30
        ami.storage_type = 'standart'

        image = Mock()
        image.root_device_name = '/sda'
        root_device = {'DeviceName': image.root_device_name,
                       'Ebs': {}}
        image.block_device_mappings = [root_device]

        res = self.deploy_operation._get_block_device_mappings(image=image,
                                                               ami_deployment_model=ami,
                                                               aws_ec2_resource_model=ec_model)

        self.assertEqual(res[0]['DeviceName'], ami.root_volume_name)
        self.assertEqual(str(res[0]['Ebs']['VolumeSize']), str(30))
        self.assertEqual(res[0]['Ebs']['DeleteOnTermination'], True)
        self.assertEqual(res[0]['Ebs']['VolumeType'], 'standart')
        self.assertFalse('Iops' in res[0]['Ebs'])

    def test_get_block_device_mappings_from_ami_with_iops(self):
        ec_model = Mock()
        ec_model.max_storage_size = 0
        ec_model.max_storage_iops = 0

        ami = Mock()
        ami.root_volume_name = 'name'
        ami.storage_size = 30
        ami.storage_iops = 300
        ami.storage_type = 'io1'

        image = Mock()
        image.root_device_name = '/sda'
        root_device = {'DeviceName': image.root_device_name,
                       'Ebs': {}}
        image.block_device_mappings = [root_device]

        res = self.deploy_operation._get_block_device_mappings(image=image,
                                                               ami_deployment_model=ami,
                                                               aws_ec2_resource_model=ec_model)

        self.assertEqual(res[0]['DeviceName'], ami.root_volume_name)
        self.assertEqual(str(res[0]['Ebs']['VolumeSize']), str(30))
        self.assertEqual(res[0]['Ebs']['DeleteOnTermination'], True)
        self.assertEqual(res[0]['Ebs']['VolumeType'], 'io1')
        self.assertEqual(res[0]['Ebs']['Iops'], 300)

    def test_create_deployment_parameters_no_ami_id(self):
        ami = Mock()
        ami.aws_ami_id = None
        self.assertRaises(ValueError,
                          self.deploy_operation._create_deployment_parameters,
                          ec2_session=Mock(),
                          aws_ec2_resource_model=self.ec2_datamodel,
                          ami_deployment_model=ami,
                          vpc=Mock(),
                          security_group=None,
                          key_pair='keypair',
                          reservation=Mock())

    def test_create_deployment_parameters(self):
        ami = Mock()
        ami.aws_ami_id = 'asd'
        ami.storage_size = '0'
        vpc = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()

        aws_model = self.deploy_operation._create_deployment_parameters(ec2_session=Mock(),
                                                                        aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation=Mock())

        self.assertEquals(aws_model.min_count, 1)
        self.assertEquals(aws_model.max_count, 1)
        self.assertEquals(aws_model.aws_key, 'keypair')
        self.assertTrue(len(aws_model.security_group_ids) == 1)
        return aws_model

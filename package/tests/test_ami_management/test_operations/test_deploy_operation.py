from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.common.exceptions import CancellationException


class TestDeployOperation(TestCase):
    def setUp(self):
        self.ec2_datamodel = Mock()
        self.ec2_session = Mock()
        self.ec2_client = Mock()
        self.s3_session = Mock()
        self.instance_service = Mock()
        self.security_group_service = Mock()
        self.tag_service = Mock()
        self.key_pair = Mock()
        self.vpc_service = Mock()
        self.subnet_service = Mock()
        self.credentials_manager = Mock()
        self.cancellation_service = Mock()
        self.logger = Mock()
        self.deploy_operation = DeployAMIOperation(self.instance_service,
                                                   self.credentials_manager,
                                                   self.security_group_service,
                                                   self.tag_service,
                                                   self.vpc_service,
                                                   self.key_pair,
                                                   self.subnet_service,
                                                   self.cancellation_service)

    def test_deploy_rollback_called(self):
        # arrange
        ami_datamodel = Mock()
        cancellation_context = Mock()
        inst_name = 'my name'
        reservation = Mock()
        self.deploy_operation._create_security_group_for_instance = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()
        self.deploy_operation._rollback_deploy = Mock()
        self.instance_service.create_instance = Mock(side_effect=Exception)

        # act & assert
        self.assertRaises(Exception, self.deploy_operation.deploy, self.ec2_session, self.s3_session, inst_name,
                          reservation, self.ec2_datamodel, ami_datamodel, self.ec2_client, cancellation_context,
                          self.logger)
        self.deploy_operation._rollback_deploy.assert_called_once()

    def test_rollback(self):
        # prepare
        self.deploy_operation._extract_instance_id_on_cancellation = Mock()
        inst_id = Mock()
        security_group = Mock()
        allocated_elastic_ip = Mock()
        instance = Mock()
        self.deploy_operation.instance_service.get_instance_by_id = Mock(return_value=instance)

        # act
        self.deploy_operation._rollback_deploy(ec2_session=self.ec2_session,
                                               instance_id=inst_id,
                                               custom_security_group=security_group,
                                               elastic_ip=allocated_elastic_ip,
                                               logger=self.logger)

        # assert
        self.deploy_operation.instance_service.get_instance_by_id.assert_called_once_with(ec2_session=self.ec2_session,
                                                                                          id=inst_id)
        self.deploy_operation.instance_service.terminate_instance.assert_called_once_with(instance=instance)
        self.deploy_operation.security_group_service.delete_security_group(security_group)
        self.deploy_operation.instance_service.find_and_release_elastic_address(ec2_session=self.ec2_session,
                                                                                elastic_ip=allocated_elastic_ip)

    def test_extract_instance_id_on_cancellation(self):
        # prepare
        instance = Mock()
        instance_id = 'some_id'
        cancellation_exception = CancellationException("cancelled_test", {'instance_ids' : [instance_id]})

        # act
        extracted_id = self.deploy_operation._extract_instance_id_on_cancellation(cancellation_exception, instance)

        # assert
        self.assertEquals(extracted_id, instance_id)

    def test_deploy(self):
        # prepare
        ami_datamodel = Mock()
        ami_datamodel.storage_size = 30
        ami_datamodel.inbound_ports = "80"
        ami_datamodel.outbound_ports = "20"
        ami_datamodel.add_public_ip = None
        ami_datamodel.allocate_elastic_ip = True
        instance = Mock()
        instance.tags = [{'Key': 'Name', 'Value': 'my name'}]
        self.instance_service.create_instance = Mock(return_value=instance)
        sg = Mock()
        self.security_group_service.create_security_group = Mock(return_value=sg)
        self.deploy_operation._get_block_device_mappings = Mock()
        cancellation_context = Mock()
        inst_name = 'my name'
        reservation = Mock()
        ami_deployment_model = Mock()
        self.deploy_operation._create_deployment_parameters = Mock(return_value=ami_deployment_model)

        # act
        res = self.deploy_operation.deploy(ec2_session=self.ec2_session,
                                           s3_session=self.s3_session,
                                           name=inst_name,
                                           reservation=reservation,
                                           aws_ec2_cp_resource_model=self.ec2_datamodel,
                                           ami_deployment_model=ami_datamodel,
                                           ec2_client=self.ec2_client,
                                           cancellation_context=cancellation_context,
                                           logger=self.logger)

        ami_credentials = self.credentials_manager.get_windows_credentials()

        # assert
        self.assertEqual(res.vm_name, 'my name')
        self.assertEqual(res.cloud_provider_resource_name, ami_datamodel.cloud_provider)
        self.assertEqual(res.auto_power_off, True)
        self.assertEqual(res.wait_for_ip, ami_datamodel.wait_for_ip)
        self.assertEqual(res.auto_delete, True)
        self.assertEqual(res.autoload, ami_datamodel.autoload)
        self.assertEqual(res.inbound_ports, ami_datamodel.inbound_ports)
        self.assertEqual(res.outbound_ports, ami_datamodel.outbound_ports)
        self.assertEqual(res.vm_uuid, instance.instance_id)
        self.assertEqual(res.deployed_app_attributes, {'Password': ami_credentials.password,
                                                       'User': ami_credentials.user_name,
                                                       'Public IP': res.elastic_ip})
        self.assertTrue(self.tag_service.get_security_group_tags.called)
        self.assertTrue(self.security_group_service.create_security_group.called)
        self.assertTrue(self.instance_service.set_ec2_resource_tags.called_with(
                self.security_group_service.create_security_group()),
                self.tag_service.get_security_group_tags())

        self.assertTrue(self.key_pair.load.called_with(self.ec2_datamodel.key_pair_location,
                                                       instance.key_pair.key_name,
                                                       self.key_pair.FILE_SYSTEM))

        self.assertTrue(self.security_group_service.set_security_group_rules.called_with(
                ami_datamodel, self.security_group_service.create_security_group()))

        self.security_group_service.remove_allow_all_outbound_rule.assert_called_with(security_group=sg)

        self.instance_service.create_instance.assert_called_once_with(ec2_session=self.ec2_session,
                                                                      name=inst_name,
                                                                      reservation=reservation,
                                                                      ami_deployment_info=ami_deployment_model,
                                                                      ec2_client=self.ec2_client,
                                                                      wait_for_status_check=ami_datamodel.wait_for_status_check,
                                                                      cancellation_context=cancellation_context,
                                                                      logger=self.logger)

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

        with self.assertRaisesRegexp(ValueError,
                                     'Requested storage size is bigger than the max allowed storage size of 30'):
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

        with self.assertRaisesRegexp(ValueError,
                                     'Requested storage IOPS is bigger than the max allowed storage IOPS of 100'):
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
        ami.storage_type = 'auto'

        image = Mock()
        image.root_device_name = '/sda'
        root_device = {'DeviceName': image.root_device_name,
                       'Ebs': {
                           'VolumeSize': '40',
                           'VolumeType': 'io1',
                           'Iops': '240',
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

    def test_get_block_device_mappings_from_app(self):
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

    def test_get_block_device_mappings_from_app_with_iops(self):
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
        image = Mock()
        image.state = 'available'
        ec2_session = Mock()
        ec2_session.Image = Mock(return_value=image)
        ami_model = Mock()
        ami_model.aws_ami_id = 'asd'
        ami_model.storage_size = '0'
        vpc = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()

        aws_model = self.deploy_operation._create_deployment_parameters(ec2_session=ec2_session,
                                                                        aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami_model,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation=Mock())

        self.assertEquals(aws_model.min_count, 1)
        self.assertEquals(aws_model.max_count, 1)
        self.assertEquals(aws_model.aws_key, 'keypair')
        self.assertTrue(len(aws_model.security_group_ids) == 1)
        return aws_model

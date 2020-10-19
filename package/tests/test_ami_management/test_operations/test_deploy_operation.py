from unittest import TestCase

from mock import Mock, call, MagicMock

from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.common.exceptions import CancellationException
from cloudshell.cp.aws.models.network_actions_models import DeployNetworkingResultModel
from cloudshell.cp.core.models import ConnectToSubnetParams, PrepareCloudInfra, ConnectSubnet


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
        self.elastic_ip_service = Mock()
        self.network_interface_service = Mock()
        self.device_index_strategy = Mock()
        self.vm_details_provider = Mock()
        self.deploy_operation = DeployAMIOperation(instance_service=self.instance_service,
                                                   ami_credential_service=self.credentials_manager,
                                                   security_group_service=self.security_group_service,
                                                   tag_service=self.tag_service,
                                                   vpc_service=self.vpc_service,
                                                   key_pair_service=self.key_pair,
                                                   subnet_service=self.subnet_service,
                                                   elastic_ip_service=self.elastic_ip_service,
                                                   network_interface_service=self.network_interface_service,
                                                   cancellation_service=self.cancellation_service,
                                                   device_index_strategy=self.device_index_strategy,
                                                   vm_details_provider=self.vm_details_provider)

    def test_deploy_rollback_called(self):
        # arrange
        ami_deploy_action = Mock()
        network_actions = None
        cancellation_context = Mock()
        inst_name = 'my name'
        reservation = Mock()
        self.deploy_operation._create_security_group_for_instance = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()
        self.deploy_operation._rollback_deploy = Mock()
        self.instance_service.create_instance = Mock(side_effect=Exception)
        self.deploy_operation._prepare_network_result_models = Mock()

        # act & assert
        self.assertRaises(Exception, self.deploy_operation.deploy, self.ec2_session, self.s3_session, inst_name,
                          reservation, self.ec2_datamodel, ami_deploy_action, network_actions, self.ec2_client, cancellation_context,
                          self.logger)
        self.deploy_operation._rollback_deploy.assert_called_once()

    def test_rollback(self):
        # prepare
        self.deploy_operation._extract_instance_id_on_cancellation = Mock()
        inst_id = Mock()
        security_group = Mock()
        instance = Mock()
        network_config_results = [Mock(public_ip='pub1'), Mock(public_ip='pub2')]
        self.deploy_operation.instance_service.get_instance_by_id = Mock(return_value=instance)

        # act
        self.deploy_operation._rollback_deploy(ec2_session=self.ec2_session,
                                               instance_id=inst_id,
                                               custom_security_group=security_group,
                                               network_config_results=network_config_results,
                                               logger=self.logger)

        # assert
        self.deploy_operation.instance_service.get_instance_by_id.assert_called_once_with(ec2_session=self.ec2_session,
                                                                                          id=inst_id)
        self.deploy_operation.instance_service.terminate_instance.assert_called_once_with(instance=instance)
        self.deploy_operation.security_group_service.delete_security_group.assert_called_once_with(security_group)
        self.deploy_operation.elastic_ip_service.find_and_release_elastic_address.assert_has_calls(
                [call(ec2_session=self.ec2_session, elastic_ip='pub1'),
                 call(ec2_session=self.ec2_session, elastic_ip='pub2')],
                any_order=True)

    def test_extract_instance_id_on_cancellation(self):
        # prepare
        instance = Mock()
        instance_id = 'some_id'
        cancellation_exception = CancellationException("cancelled_test", {'instance_ids': [instance_id]})

        # act
        extracted_id = self.deploy_operation._extract_instance_id_on_cancellation(cancellation_exception, instance)

        # assert
        self.assertEquals(extracted_id, instance_id)

    def test_deploy(self):
        # prepare
        ami_datamodel = self._create_ami_datamodel()
        ami_deploy_action = self._create_ami_deploy_action(ami_datamodel)
        ami_deployment_info = Mock()
        instance = self._create_instance()
        network_config_results = [Mock(device_index=0, public_ip=instance.public_ip_address)]
        self.instance_service.create_instance = Mock(return_value=instance)
        sg = Mock()
        self.security_group_service.create_security_group = Mock(return_value=sg)

        self._mock_deploy_operation(ami_deployment_info, network_config_results)

        cancellation_context = Mock()
        inst_name = 'my name'
        reservation = Mock()
        network_actions = None

        # act

        res = self.deploy_operation.deploy(ec2_session=self.ec2_session,
                                           s3_session=self.s3_session,
                                           name=inst_name,
                                           reservation=reservation,
                                           aws_ec2_cp_resource_model=self.ec2_datamodel,
                                           ami_deploy_action=ami_deploy_action,
                                           network_actions=network_actions,
                                           ec2_client=self.ec2_client,
                                           cancellation_context=cancellation_context,
                                           logger=self.logger)

        ami_credentials = self.credentials_manager.get_windows_credentials()

        # assert
        self.assertEqual(res[0].vmName, 'my name')
        self.assertEqual(res[0].deployedAppAdditionalData["inbound_ports"], ami_datamodel.inbound_ports)
        self.assertEqual(res[0].vmUuid, instance.instance_id)
        self.assertEqual(res[0].deployedAppAttributes[0].attributeName, 'Password')
        self.assertEqual(res[0].deployedAppAttributes[0].attributeValue, ami_credentials.password)
        self.assertEqual(res[0].deployedAppAttributes[1].attributeName, 'User')
        self.assertEqual(res[0].deployedAppAttributes[1].attributeValue, ami_credentials.user_name)
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
                                                                      ami_deployment_info=ami_deployment_info,
                                                                      ec2_client=self.ec2_client,
                                                                      wait_for_status_check=ami_datamodel.wait_for_status_check,
                                                                      cancellation_context=cancellation_context,
                                                                      logger=self.logger)

        self.deploy_operation.elastic_ip_service.set_elastic_ips.assert_called_once_with(
                ec2_session=self.ec2_session,
                ec2_client=self.ec2_client,
                instance=instance,
                ami_deployment_model=ami_datamodel,
                network_actions=None,
                network_config_results=network_config_results,
                logger=self.logger)

    def test_2ndGen_deployed_app_with_namespaced_user(self):
        # prepare
        ami_datamodel = self._create_ami_datamodel()
        ami_deploy_action = self._create_ami_deploy_action(ami_datamodel)
        ami_deployment_info = Mock()
        instance = self._create_instance()
        instance.platform = None
        network_config_results = [Mock(device_index=0, public_ip=instance.public_ip_address)]
        self.instance_service.create_instance = Mock(return_value=instance)
        sg = Mock()
        self.security_group_service.create_security_group = Mock(return_value=sg)

        self._mock_deploy_operation(ami_deployment_info, network_config_results)

        cancellation_context = Mock()
        inst_name = 'my name'
        reservation = Mock()
        network_actions = None

        # act

        res = self.deploy_operation.deploy(ec2_session=self.ec2_session,
                                           s3_session=self.s3_session,
                                           name=inst_name,
                                           reservation=reservation,
                                           aws_ec2_cp_resource_model=self.ec2_datamodel,
                                           ami_deploy_action=ami_deploy_action,
                                           network_actions=network_actions,
                                           ec2_client=self.ec2_client,
                                           cancellation_context=cancellation_context,
                                           logger=self.logger)

        ami_credentials = self.credentials_manager.get_windows_credentials()

        # assert
        self.assertEqual(res[0].vmName, 'my name')
        self.assertEqual(res[0].deployedAppAdditionalData["inbound_ports"], ami_datamodel.inbound_ports)
        self.assertEqual(res[0].vmUuid, instance.instance_id)
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
                                                                      ami_deployment_info=ami_deployment_info,
                                                                      ec2_client=self.ec2_client,
                                                                      wait_for_status_check=ami_datamodel.wait_for_status_check,
                                                                      cancellation_context=cancellation_context,
                                                                      logger=self.logger)

        self.deploy_operation.elastic_ip_service.set_elastic_ips.assert_called_once_with(
                ec2_session=self.ec2_session,
                ec2_client=self.ec2_client,
                instance=instance,
                ami_deployment_model=ami_datamodel,
                network_actions=None,
                network_config_results=network_config_results,
                logger=self.logger)

    def _mock_deploy_operation(self, ami_deployment_info, network_config_results):
        self.deploy_operation._get_block_device_mappings = Mock()
        self.deploy_operation._create_deployment_parameters = Mock(return_value=ami_deployment_info)
        self.deploy_operation._populate_network_config_results_with_interface_data = Mock()
        self.deploy_operation._prepare_network_result_models = Mock(return_value=network_config_results)
        self.deploy_operation._prepare_network_config_results_dto = Mock(return_value=[])

    def _create_instance(self):
        instance = Mock()
        instance.network_interfaces = []
        instance.tags = [{'Key': 'Name', 'Value': 'my name'}]
        return instance

    def _create_ami_deploy_action(self, ami_datamodel):
        ami_deploy_action = Mock()
        ami_deploy_action.actionParms = Mock()
        ami_deploy_action.actionParams.deployment = Mock()
        ami_deploy_action.actionParams.deployment.customModel = ami_datamodel
        ami_deploy_action.actionParams.appResource.attributes = {"gen2.User": "lala"}
        return ami_deploy_action

    def _create_ami_datamodel(self):
        ami_datamodel = Mock()
        ami_datamodel.storage_size = 30
        ami_datamodel.inbound_ports = "80"
        ami_datamodel.outbound_ports = "20"
        ami_datamodel.add_public_ip = None
        ami_datamodel.allocate_elastic_ip = True
        return ami_datamodel

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
        network_actions = MagicMock()
        ami.aws_ami_id = None
        self.assertRaises(ValueError,
                          self.deploy_operation._create_deployment_parameters,
                          ec2_session=Mock(),
                          aws_ec2_resource_model=self.ec2_datamodel,
                          ami_deployment_model=ami,
                          network_actions=network_actions,
                          vpc=Mock(),
                          security_group=None,
                          key_pair='keypair',
                          reservation=Mock(),
                          network_config_results=Mock(),
                          logger=self.logger)

    def test_create_deployment_parameters_single_subnet(self):
        image = Mock()
        image.state = 'available'
        ec2_session = Mock()
        ec2_session.Image = Mock(return_value=image)
        ami_model = Mock()
        ami_model.aws_ami_id = 'asd'
        ami_model.storage_size = '0'
        ami_model.iam_role = ""
        ami_model.custom_tags= ""

        network_actions = None
        vpc = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()

        aws_model = self.deploy_operation._create_deployment_parameters(ec2_session=ec2_session,
                                                                        aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami_model,
                                                                        network_actions=network_actions,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation=Mock(),
                                                                        network_config_results=MagicMock(),
                                                                        logger=self.logger)

        self.assertEquals(aws_model.min_count, 1)
        self.assertEquals(aws_model.max_count, 1)
        self.assertEquals(aws_model.aws_key, 'keypair')
        self.assertTrue(len(aws_model.security_group_ids) == 1)
        self.assertTrue(len(aws_model.network_interfaces) == 1)

    def test_create_deployment_parameters_no_iam_role(self):
        image = Mock()
        image.state = 'available'
        ec2_session = Mock()
        ec2_session.Image = Mock(return_value=image)
        ami_model = Mock()
        ami_model.iam_role = ""
        ami_model.custom_tags = ""
        network_actions = None
        vpc = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()

        aws_model = self.deploy_operation._create_deployment_parameters(ec2_session=ec2_session,
                                                                        aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami_model,
                                                                        network_actions=network_actions,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation=Mock(),
                                                                        network_config_results=MagicMock(),
                                                                        logger=self.logger,)

        # if instance doesnt have iam role, the deployment params will have an empty iam instance profile dict
        self.assertTrue(not any(aws_model.iam_role))  # not any(some_dict) => is empty dictionary

    def test_create_deployment_parameters_iam_role_not_arn(self):
        image = Mock()
        image.state = 'available'
        ec2_session = Mock()
        ec2_session.Image = Mock(return_value=image)
        ami_model = Mock()
        ami_model.iam_role = "admin_role"
        ami_model.custom_tags = ""

        vpc = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()
        network_actions = None

        aws_model = self.deploy_operation._create_deployment_parameters(ec2_session=ec2_session,
                                                                        aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami_model,
                                                                        network_actions=network_actions,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation=Mock(),
                                                                        network_config_results=MagicMock(),
                                                                        logger=self.logger,)

        # if instance has iam role, but not in the form of arn, will return dict with iam role name
        self.assertTrue(aws_model.iam_role['Name'] == ami_model.iam_role)

    def test_create_deployment_parameters_iam_role_arn(self):
        image = Mock()
        image.state = 'available'
        ec2_session = Mock()
        ec2_session.Image = Mock(return_value=image)
        ami_model = Mock()
        network_actions = None
        ami_model.iam_role = "arn:aws:iam::admin_role"
        ami_model.custom_tags = ""
        vpc = Mock()
        self.deploy_operation._get_block_device_mappings = Mock()

        aws_model = self.deploy_operation._create_deployment_parameters(ec2_session=ec2_session,
                                                                        aws_ec2_resource_model=self.ec2_datamodel,
                                                                        ami_deployment_model=ami_model,
                                                                        network_actions=network_actions,
                                                                        vpc=vpc,
                                                                        security_group=None,
                                                                        key_pair='keypair',
                                                                        reservation=Mock(),
                                                                        network_config_results=MagicMock(),
                                                                        logger=self.logger)

        # if instance has iam role, but not in the form of arn, will return dict with iam role name
        self.assertTrue(aws_model.iam_role['Arn'] == ami_model.iam_role)

    def test_prepare_network_interfaces_multi_subnets_with_public_ip(self):
        ami_model = Mock()
        ami_model.add_public_ip = True
        ami_model.network_configurations = [Mock(), Mock()]

        network_actions = [Mock(spec=ConnectSubnet),Mock(spec=ConnectSubnet)]

        with self.assertRaisesRegexp(ValueError, "Public IP option is not supported with multiple subnets"):
            self.deploy_operation._prepare_network_interfaces(ami_deployment_model=ami_model,
                                                              network_actions=network_actions,
                                                              vpc=Mock(),
                                                              security_group_ids=MagicMock(),
                                                              network_config_results=MagicMock(),
                                                              logger=self.logger)

    def test_prepare_network_interfaces_multi_subnets(self):
        def build_network_interface_handler(*args, **kwargs):
            return {'SubnetId': kwargs['subnet_id']}

        # arrange
        vpc = Mock()
        security_group_ids = MagicMock()

        action1 = ConnectSubnet()
        action1.actionId = 'action1'
        action1.actionParams = ConnectToSubnetParams()
        action1.actionParams.subnetId= 'sub1'
        action1.actionParams.vnicName = 0
        action1.actionParams.isPublic = True

        action2 = ConnectSubnet()
        action2.actionId = 'action2'
        action2.actionParams = ConnectToSubnetParams()
        action2.actionParams.subnetId = 'sub2'
        action2.actionParams.vnicName = 1

        ami_model = Mock()
        network_actions = [action1, action2]
        ami_model.add_public_ip = False

        res_model_1 = DeployNetworkingResultModel('action1')
        res_model_2 = DeployNetworkingResultModel('action2')
        network_config_results = [res_model_1, res_model_2]

        self.deploy_operation.network_interface_service.build_network_interface_dto = \
            Mock(side_effect=build_network_interface_handler)

        # act
        net_interfaces = self.deploy_operation._prepare_network_interfaces(ami_deployment_model=ami_model,
                                                                           network_actions=network_actions,
                                                                           vpc=vpc,
                                                                           security_group_ids=security_group_ids,
                                                                           network_config_results=network_config_results,
                                                                           logger=self.logger)

        # assert
        print res_model_1.device_index
        self.assertEquals(res_model_1.device_index, 0)
        self.assertEquals(res_model_2.device_index, 1)
        self.assertEquals(len(net_interfaces), 2)
        self.assertEquals(net_interfaces[0]['SubnetId'], 'sub1')
        self.assertEquals(net_interfaces[1]['SubnetId'], 'sub2')

    def test_prepare_network_config_results_dto_returns_empty_array_when_no_network_config(self):
        # arrange
        network_actions = None


        # act
        dtos = self.deploy_operation._prepare_network_config_results_dto(Mock(), network_actions)

        # assert
        self.assertTrue(isinstance(dtos, list))
        self.assertFalse(dtos)

    def test_prepare_network_config_results_dto(self):
        # arrange
        model1 = DeployNetworkingResultModel(action_id='aaa')
        model1.device_index = 0
        model1.interface_id = "interface1"
        model1.mac_address = "mac1"
        model1.private_ip = "priv1"
        model1.public_ip = "pub1"

        model2 = DeployNetworkingResultModel(action_id='bbb')
        model2.device_index = 1
        model2.interface_id = "interface2"
        model2.mac_address = "mac2"
        model2.private_ip = "priv2"
        model2.public_ip = "pub2"

        models = [model1, model2]

        network_actions = Mock()
        # act
        dtos = self.deploy_operation._prepare_network_config_results_dto(models, network_actions)

        self.assertEquals(len(dtos), 2)
        dto1 = dtos[0]
        dto2 = dtos[1]
        self.assertEquals(dto1.actionId, "aaa")
        self.assertEquals(dto2.actionId, "bbb")
        self.assertTrue(dto1.success)
        self.assertTrue(dto2.success)
        self.assertEquals(dto1.type, "ConnectToSubnet")
        self.assertEquals(dto2.type, "ConnectToSubnet")
        self.assertTrue('"interface_id": "interface1"' in dto1.interface)
        self.assertTrue('"Device Index": 0' in dto1.interface)
        self.assertTrue('"IP": "priv1"' in dto1.interface)
        self.assertTrue('"Public IP": "pub1"' in dto1.interface)
        self.assertTrue('"MAC Address": "mac1"' in dto1.interface)

    def test_deploy_raised_no_vpc(self):
        # arrange
        my_vpc_service = Mock()
        my_vpc_service.find_vpc_for_reservation = Mock(return_value=None)
        deploy_operation = DeployAMIOperation(self.instance_service,
                                              self.credentials_manager,
                                              self.security_group_service,
                                              self.tag_service,
                                              my_vpc_service,
                                              self.key_pair,
                                              self.subnet_service,
                                              self.elastic_ip_service,
                                              self.network_interface_service,
                                              self.cancellation_service,
                                              self.device_index_strategy,
                                              self.vm_details_provider)

        # act & assert
        with self.assertRaisesRegexp(ValueError, 'VPC is not set for this reservation'):
            deploy_operation.deploy(ec2_session=Mock(),
                                    s3_session=Mock(),
                                    name=Mock(),
                                    reservation=Mock(),
                                    aws_ec2_cp_resource_model=Mock(),
                                    ami_deploy_action=Mock(),
                                    network_actions=Mock(),
                                    ec2_client=Mock(),
                                    cancellation_context=Mock(),
                                    logger=self.logger)

    def test__prepare_network_result_models_returns_empty_model_when_no_network_config(self):
        # arrange
        network_actions = None

        # act
        models = self.deploy_operation._prepare_network_result_models(network_actions)

        # assert
        self.assertEquals(len(models), 1)
        self.assertEquals(models[0].action_id, '')
        self.assertTrue(isinstance(models[0], DeployNetworkingResultModel))

    def test__prepare_network_result_models_returns_result_model_per_action(self):
        # arrange
        action1 = Mock(spec=PrepareCloudInfra, actionId=Mock(spec=str))
        action1.actionParams = Mock(spec=ConnectToSubnetParams)

        action2 = Mock(spec=PrepareCloudInfra, actionId=Mock(spec=str))
        action2.actionParams = Mock(spec=ConnectToSubnetParams)

        network_actions = [action1, action2]

        # act
        models = self.deploy_operation._prepare_network_result_models(network_actions)

        # assert
        self.assertEquals(len(models), 2)
        self.assertTrue(isinstance(models[0], DeployNetworkingResultModel))
        self.assertTrue(isinstance(models[1], DeployNetworkingResultModel))
        self.assertEquals(models[0].action_id, action1.actionId)
        self.assertEquals(models[1].action_id, action2.actionId)

    def test_populate_network_config_results_with_interface_data(self):
        # arrange
        instance = Mock()
        instance.network_interfaces_attribute = [
            {
                "Attachment": {"DeviceIndex": 0},
                "NetworkInterfaceId": "int1",
                "PrivateIpAddress": "pri_ip_1",
                "MacAddress": "mac1",
                "Association": {"PublicIp": "pub_ip_1"}
            },
            {
                "Attachment": {"DeviceIndex": 1},
                "NetworkInterfaceId": "int2",
                "PrivateIpAddress": "pri_ip_2",
                "MacAddress": "mac2"
            }
        ]
        network_config_results = [DeployNetworkingResultModel("action1"), DeployNetworkingResultModel("action2")]
        network_config_results[0].device_index = 0
        network_config_results[1].device_index = 1

        # act
        self.deploy_operation._populate_network_config_results_with_interface_data(
                instance=instance,
                network_config_results=network_config_results)

        # assert
        self.assertEquals(network_config_results[0].interface_id, "int1")
        self.assertEquals(network_config_results[0].private_ip, "pri_ip_1")
        self.assertEquals(network_config_results[0].mac_address, "mac1")
        self.assertEquals(network_config_results[0].public_ip, "pub_ip_1")

        self.assertEquals(network_config_results[1].interface_id, "int2")
        self.assertEquals(network_config_results[1].private_ip, "pri_ip_2")
        self.assertEquals(network_config_results[1].mac_address, "mac2")
        self.assertEquals(network_config_results[1].public_ip, "")

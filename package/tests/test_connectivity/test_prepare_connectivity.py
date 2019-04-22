from unittest import TestCase

from mock import Mock, MagicMock, patch

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareSandboxInfraOperation
from cloudshell.cp.core.models import PrepareCloudInfra
from cloudshell.cp.core.models import PrepareSubnet
from cloudshell.cp.core.models import PrepareSubnetParams
from cloudshell.cp.core.models import PrepareCloudInfraParams
from cloudshell.cp.core.models import CreateKeys

class TestPrepareSandboxInfra(TestCase):
    def setUp(self):
        self.vpc_serv = Mock()
        self.vpc_serv.get_all_internet_gateways = Mock(return_value=[])

        self.sg_serv = Mock()
        self.key_pair_serv = Mock()
        self.ec2_session = Mock()
        self.ec2_client = Mock()
        self.s3_session = Mock()
        self.aws_dm = Mock()
        self.tag_service = Mock()
        self.reservation = Mock()
        self.route_table_service = Mock()
        self.cancellation_service = Mock()
        self.cancellation_context = Mock()
        self.subnet_service = Mock()
        self.subnet_waiter = Mock()
        self.prepare_conn = PrepareSandboxInfraOperation(self.vpc_serv, self.sg_serv, self.key_pair_serv,
                                                         self.tag_service, self.route_table_service,
                                                         self.cancellation_service,
                                                         self.subnet_service, self.subnet_waiter)

    def test_prepare_conn_must_receive_network_action(self):
        with self.assertRaises(Exception) as error:
            self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                   ec2_session=self.ec2_session,
                                                   s3_session=self.s3_session,
                                                   reservation=self.reservation,
                                                   aws_ec2_datamodel=self.aws_dm,
                                                   actions=[PrepareSubnet()],
                                                   cancellation_context=self.cancellation_context,
                                                   logger=Mock())
        self.assertEqual(error.exception.message, "Actions list must contain a PrepareCloudInfraAction.")

    def test_prepare_conn_execute_the_network_action_first(self):
        # Arrage
        actions = []
        prepare_subnet_sub_a = PrepareSubnet();
        prepare_subnet_sub_a.actionId = "SubA"
        prepare_subnet_sub_a.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_a)
        prepare_cloud_infra = PrepareCloudInfra()
        prepare_cloud_infra.actionId = "Net"
        prepare_cloud_infra.actionParams = PrepareCloudInfraParams()
        actions.append(prepare_cloud_infra)
        prepare_subnet_sub_b = PrepareSubnet();
        prepare_subnet_sub_b.actionId = "SubB"
        prepare_subnet_sub_b.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_b)
        prepare_create_key = CreateKeys();
        prepare_create_key.actionId = "CreateKeys"
        actions.append(prepare_create_key)
        # Act
        results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                         ec2_session=self.ec2_session,
                                                         s3_session=self.s3_session,
                                                         reservation=self.reservation,
                                                         aws_ec2_datamodel=self.aws_dm,
                                                         actions=actions,
                                                         cancellation_context=self.cancellation_context,
                                                         logger=Mock())
        # Assert
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].actionId, "Net")
        self.assertEqual(results[1].actionId, "CreateKeys")
        self.assertEqual(results[2].actionId, "SubA")
        self.assertEqual(results[3].actionId, "SubB")

    def test_prepare_conn_execute_the_subnet_actions(self):
        # Arrage
        actions = []
        prepare_subnet_sub_a = PrepareSubnet();
        prepare_subnet_sub_a.actionId = "SubA"
        prepare_subnet_sub_a.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_a)
        prepare_cloud_infra = PrepareCloudInfra()
        prepare_cloud_infra.actionId = "Net"
        prepare_cloud_infra.actionParams = PrepareCloudInfraParams()
        actions.append(prepare_cloud_infra)
        prepare_subnet_sub_b = PrepareSubnet();
        prepare_subnet_sub_b.actionId = "SubB"
        prepare_subnet_sub_b.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_b)
        prepare_create_key = CreateKeys();
        prepare_create_key.actionId = "CreateKeys"
        actions.append(prepare_create_key)
        # Act
        with patch('cloudshell.cp.aws.domain.conncetivity.operations.prepare.PrepareSubnetExecutor') as ctor:
            obj = Mock()
            obj.execute = Mock(return_value=["ResA", "ResB"])
            ctor.return_value = obj
            results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                             ec2_session=self.ec2_session,
                                                             s3_session=self.s3_session,
                                                             reservation=self.reservation,
                                                             aws_ec2_datamodel=self.aws_dm,
                                                             actions=actions,
                                                             cancellation_context=self.cancellation_context,
                                                             logger=Mock())
        # Assert
        self.assertEqual(len(results), 4)
        self.assertEqual(results[2], "ResA")
        self.assertEqual(results[3], "ResB")

    def test_prepare_conn_command(self):
        # Arrange
        action = PrepareCloudInfra()
        action.actionId = "1234"
        action.actionParams = PrepareCloudInfraParams()

        action2 = CreateKeys()
        action2.actionId = "123"

        self.vpc_serv.get_peering_connection_by_reservation_id = Mock(return_value=None)
        access_key = Mock()
        self.prepare_conn._get_or_create_key_pair = Mock(return_value=access_key)
        self.route_table_service.get_all_route_tables = Mock(return_value=MagicMock())

        results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                         ec2_session=self.ec2_session,
                                                         s3_session=self.s3_session,
                                                         reservation=self.reservation,
                                                         aws_ec2_datamodel=self.aws_dm,
                                                         actions=[action,action2],
                                                         cancellation_context=self.cancellation_context,
                                                         logger=Mock())


        self.assertEqual(results[0].actionId, action.actionId)
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].infoMessage, 'PrepareCloudInfra finished successfully')
        self.assertEqual(results[0].errorMessage, '')
        self.assertEqual(results[1].actionId, action2.actionId)
        self.assertTrue(results[1].success)
        self.assertEqual(results[1].infoMessage, 'PrepareCreateKeys finished successfully')
        self.assertEqual(results[1].errorMessage, '')
        self.assertEqual(results[1].accessKey, access_key)
        self.cancellation_service.check_if_cancelled.assert_called()

    def test_prepare_conn_command_no_management_vpc(self):
        request = Mock()
        aws_dm = Mock()
        cancellation_context = Mock()
        aws_dm.aws_management_vpc_id = None
        self.assertRaises(ValueError,
                          self.prepare_conn.prepare_connectivity,
                          self.ec2_client,
                          self.ec2_session,
                          self.s3_session,
                          self.reservation,
                          aws_dm,
                          request,
                          cancellation_context,
                          Mock())

    def test_prepare_conn_error_no_vpc_with_vpc_count(self):
        self.vpc_serv.find_vpc_for_reservation = Mock(return_value=None)

        vpc_count = 50
        self.vpc_serv.get_active_vpcs_count = Mock(return_value=vpc_count)

        # Arrage
        actions = []
        prepare_subnet_sub_a = PrepareSubnet();
        prepare_subnet_sub_a.actionId = "SubA"
        prepare_subnet_sub_a.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_a)
        prepare_cloud_infra = PrepareCloudInfra()
        prepare_cloud_infra.actionId = "Net"
        prepare_cloud_infra.actionParams = PrepareCloudInfraParams()
        actions.append(prepare_cloud_infra)
        prepare_subnet_sub_b = PrepareSubnet();
        prepare_subnet_sub_b.actionId = "SubB"
        prepare_subnet_sub_b.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_b)
        prepare_create_key = CreateKeys();
        prepare_create_key.actionId = "CreateKeys"
        actions.append(prepare_create_key)

        # Assert
        self.assertRaisesRegexp(ValueError,
                                '(/{0}/)|(limit.$)'.format(vpc_count),
                                self.prepare_conn.prepare_connectivity,
                                ec2_client=self.ec2_client,
                                ec2_session=self.ec2_session,
                                s3_session=self.s3_session,
                                reservation=self.reservation,
                                aws_ec2_datamodel=self.aws_dm,
                                actions=actions,
                                cancellation_context=self.cancellation_context,
                                logger=Mock())

    def test_prepare_conn_error_no_vpc(self):
        self.vpc_serv.find_vpc_for_reservation = Mock(return_value=None)
        self.vpc_serv.get_active_vpcs_count = Mock(return_value=None)

        # Arrage
        actions = []
        prepare_subnet_sub_a = PrepareSubnet();
        prepare_subnet_sub_a.actionId = "SubA"
        prepare_subnet_sub_a.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_a)
        prepare_cloud_infra = PrepareCloudInfra()
        prepare_cloud_infra.actionId = "Net"
        prepare_cloud_infra.actionParams = PrepareCloudInfraParams()
        actions.append(prepare_cloud_infra)
        prepare_subnet_sub_b = PrepareSubnet();
        prepare_subnet_sub_b.actionId = "SubB"
        prepare_subnet_sub_b.actionParams = PrepareSubnetParams()
        actions.append(prepare_subnet_sub_b)

        # Assert
        self.assertRaisesRegexp(ValueError,
                                '^((?!limit).)*$',
                                self.prepare_conn.prepare_connectivity,
                                ec2_client=self.ec2_client,
                                ec2_session=self.ec2_session,
                                s3_session=self.s3_session,
                                reservation=self.reservation,
                                aws_ec2_datamodel=self.aws_dm,
                                actions=actions,
                                cancellation_context=self.cancellation_context,
                                logger=Mock())

    def test_prepare_conn_command_fault_res(self):
        self.aws_dm.is_static_vpc_mode = False

        action = PrepareCloudInfra()
        action.actionId="1234"
        action.actionParams = PrepareCloudInfraParams()
        action.actionParams.cidr = "1.2.3.4/24"
        action2 = CreateKeys()
        action2.actionId="123"
        cancellation_context = Mock()

        results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                         ec2_session=self.ec2_session,
                                                         s3_session=self.s3_session,
                                                         reservation=self.reservation,
                                                         aws_ec2_datamodel=self.aws_dm,
                                                         actions=[action, action2],
                                                         cancellation_context=cancellation_context,
                                                         logger=Mock())

        self.assertFalse(results[0].success)
        self.assertEqual(results[0].infoMessage, '')
        self.assertIsNotNone(results[0].errorMessage)

    def test_create_key_pair(self):
        key_pair_service = Mock()
        key_pair_service.load_key_pair_by_name = Mock(return_value=None)
        prepare_conn = PrepareSandboxInfraOperation(self.vpc_serv, self.sg_serv, key_pair_service, self.tag_service,
                                                    self.route_table_service,
                                                    self.cancellation_service,
                                                    self.subnet_service, self.subnet_waiter)
        key_pair = Mock()
        key_pair_service.create_key_pair = Mock(return_value=key_pair)

        access_key = prepare_conn._get_or_create_key_pair(self.ec2_session, self.s3_session, 'bucket', 'res_id')

        key_pair_service.load_key_pair_by_name.assert_called_once_with(s3_session=self.s3_session, bucket_name='bucket', reservation_id='res_id')
        key_pair_service.create_key_pair.assert_called_once_with(ec2_session=self.ec2_session, s3_session=self.s3_session, bucket='bucket', reservation_id='res_id')
        self.assertEquals(access_key, key_pair.key_material)

    def test_get_or_create_security_groups(self):
        sg = Mock()
        vpc = Mock()
        sg_name = Mock()
        isolated_sg = Mock()
        management_sg_id = Mock()
        security_group_service = Mock()
        security_group_service.get_security_group_name = Mock(return_value=sg_name)
        security_group_service.get_security_group_by_name = Mock(return_value=None)
        security_group_service.create_security_group = Mock(return_value=sg)


        prepare_conn = PrepareSandboxInfraOperation(self.vpc_serv, security_group_service, self.key_pair_serv,
                                                    self.tag_service, self.route_table_service,
                                                    self.cancellation_service,
                                                    self.subnet_service, self.subnet_waiter)

        prepare_conn._get_or_create_sandbox_isolated_security_group = Mock(return_value=isolated_sg)

        res = prepare_conn._get_or_create_default_security_groups(self.ec2_session, self.reservation, vpc,
                                                                  management_sg_id, True)

        security_group_service.get_security_group_by_name.assert_called_with(vpc=vpc,
                                                                             name=security_group_service.sandbox_default_sg_name())

        security_group_service.create_security_group.assert_called_with(ec2_session=self.ec2_session,
                                                                             vpc_id=vpc.id,
                                                                             security_group_name=security_group_service.sandbox_default_sg_name())

        self.tag_service.get_sandbox_default_security_group_tags.assert_called_once_with(name=security_group_service.sandbox_default_sg_name(),
                                                                                         reservation=self.reservation)

        security_group_service.set_shared_reservation_security_group_rules.assert_called_once_with(security_group=sg,
                                                                                                   management_sg_id=management_sg_id,
                                                                                                   isolated_sg=isolated_sg,
                                                                                                   need_management_sg=True)
        self.assertEqual([isolated_sg, sg], res)  # create two security groups, default and isolated

    def test_get_or_create_default_sandbox_security_group(self):
        sg_name = Mock()
        sg = Mock()
        vpc = Mock()
        management_sg_id = Mock()
        isolated_sg = Mock()
        security_group_service = Mock()
        security_group_service.sandbox_default_sg_name = Mock(return_value=sg_name)
        security_group_service.get_security_group_by_name = Mock(return_value=None)
        security_group_service.create_security_group = Mock(return_value=sg)
        security_group_service.set_shared_reservation_security_group_rules = Mock()

        tags = Mock()
        self.tag_service.get_sandbox_default_security_group_tags = Mock(return_value=tags)

        prepare_conn = PrepareSandboxInfraOperation(self.vpc_serv, security_group_service, self.key_pair_serv,
                                                    self.tag_service, self.route_table_service,
                                                    self.cancellation_service,
                                                    self.subnet_service, self.subnet_waiter)

        res = prepare_conn._get_or_create_sandbox_default_security_group(ec2_session=self.ec2_session,
                                                                         management_sg_id=management_sg_id,
                                                                         reservation=self.reservation,
                                                                         vpc=vpc,
                                                                         isolated_sg=isolated_sg,
                                                                         need_management_access=True)

        security_group_service.get_security_group_by_name.assert_called_once_with(vpc=vpc, name=sg_name)
        security_group_service.create_security_group.assert_called_once_with(ec2_session=self.ec2_session,
                                                                             vpc_id=vpc.id,
                                                                             security_group_name=sg_name)
        self.tag_service.get_sandbox_default_security_group_tags.assert_called_once_with(name=sg_name,
                                                                                         reservation=self.reservation)
        self.tag_service.set_ec2_resource_tags.assert_called_once_with(sg, tags)

        security_group_service.set_shared_reservation_security_group_rules.assert_called_once_with(security_group=sg,
                                                                                                   management_sg_id=management_sg_id,
                                                                                                   isolated_sg=isolated_sg,
                                                                                                   need_management_sg=True)
        self.assertEqual(sg, res)

    def test_get_or_create_isolated_security_group(self):
        sg_name = Mock()
        sg = Mock()
        vpc = Mock()
        management_sg_id = Mock()
        security_group_service = Mock()
        isolated_sg_name = 'all alone in the watch tower'
        security_group_service.get_security_group_by_name = Mock(return_value=None)
        security_group_service.create_security_group = Mock(return_value=sg)
        security_group_service.sandbox_default_sg_name = Mock(return_value=sg_name)
        security_group_service.sandbox_isolated_sg_name = Mock(return_value=isolated_sg_name)

        prepare_conn = PrepareSandboxInfraOperation(self.vpc_serv, security_group_service, self.key_pair_serv,
                                                    self.tag_service, self.route_table_service,
                                                    self.cancellation_service,
                                                    self.subnet_service, self.subnet_waiter)

        res = prepare_conn._get_or_create_sandbox_isolated_security_group(ec2_session=self.ec2_session,
                                                                          management_sg_id=management_sg_id,
                                                                          reservation=self.reservation,
                                                                          vpc=vpc,
                                                                          need_management_access=True)
        security_group_service.get_security_group_by_name.assert_called_once_with(vpc=vpc, name=isolated_sg_name)

        security_group_service.create_security_group.assert_called_once_with(ec2_session=self.ec2_session,
                                                                             vpc_id=vpc.id,
                                                                             security_group_name=isolated_sg_name)
        security_group_service.sandbox_isolated_sg_name.assert_called_once_with(self.reservation.reservation_id)
        self.assertEqual(sg, res)

    def test_get_or_create_vpc(self):
        cidr = Mock()
        vpc = Mock()
        vpc_service = Mock()
        vpc_service.find_vpc_for_reservation = Mock(return_value=None)
        vpc_service.create_vpc_for_reservation = Mock(return_value=vpc)

        prepare_conn = PrepareSandboxInfraOperation(vpc_service, self.sg_serv, self.key_pair_serv, self.tag_service,
                                                    self.route_table_service,
                                                    self.cancellation_service,
                                                    self.subnet_service, self.subnet_waiter)

        result = prepare_conn._get_or_create_vpc(cidr=cidr,
                                              ec2_session=self.ec2_session,
                                              reservation=self.reservation)

        vpc_service.find_vpc_for_reservation.assert_called_once_with(ec2_session=self.ec2_session,
                                                                     reservation_id=self.reservation.reservation_id)

        vpc_service.create_vpc_for_reservation.assert_called_once_with(ec2_session=self.ec2_session,
                                                                       reservation=self.reservation,
                                                                       cidr=cidr)

        self.assertEqual(vpc, result)

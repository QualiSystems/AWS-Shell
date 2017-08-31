from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareConnectivityOperation
from cloudshell.cp.aws.models.network_actions_models import *

class TestPrepareConnectivity(TestCase):
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
        self.crypto_service = Mock()
        self.cancellation_service = Mock()
        self.cancellation_context = Mock()

        self.prepare_conn = PrepareConnectivityOperation(self.vpc_serv, self.sg_serv, self.key_pair_serv,
                                                         self.tag_service, self.route_table_service,
                                                         self.crypto_service, self.cancellation_service)

    def test_prepare_conn_must_receive_network_action(self):
        with self.assertRaises(Exception) as error:
            self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                   ec2_session=self.ec2_session,
                                                   s3_session=self.s3_session,
                                                   reservation=self.reservation,
                                                   aws_ec2_datamodel=self.aws_dm,
                                                   actions=[NetworkAction()],
                                                   cancellation_context=self.cancellation_context,
                                                   logger=Mock())
        self.assertEqual(error.exception.message, "Actions list must contain a PrepareNetworkAction.")

    def test_prepare_conn_execute_the_network_action_first(self):
        # Arrage
        actions = []
        actions.append(NetworkAction(id="SubA", connection_params=PrepareSubnetParams()))
        actions.append(NetworkAction(id="Net", connection_params=PrepareNetworkParams()))
        actions.append(NetworkAction(id="SubB", connection_params=PrepareSubnetParams()))
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
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].actionId, "Net")
        self.assertEqual(results[1].actionId, "SubA")
        self.assertEqual(results[2].actionId, "SubB")

    def test_prepare_subnet_must_have_a_vpc(self):
        # Arrage
        # Act
        # Assert
        pass

    def test_prepare_conn_command(self):
        # Arrange
        action = NetworkAction(id="1234", connection_params=PrepareNetworkParams())

        self.vpc_serv.get_peering_connection_by_reservation_id = Mock(return_value=None)
        access_key = Mock()
        self.prepare_conn._get_or_create_key_pair = Mock(return_value=access_key)
        crypto_dto = Mock()
        self.crypto_service.encrypt = Mock(return_value=crypto_dto)
        self.route_table_service.get_all_route_tables = Mock(return_value=MagicMock())


        results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                         ec2_session=self.ec2_session,
                                                         s3_session=self.s3_session,
                                                         reservation=self.reservation,
                                                         aws_ec2_datamodel=self.aws_dm,
                                                         actions=[action],
                                                         cancellation_context=self.cancellation_context,
                                                         logger=Mock())

        self.prepare_conn._get_or_create_key_pair.assert_called_once_with(ec2_session=self.ec2_session,
                                                                          s3_session=self.s3_session,
                                                                          bucket=self.aws_dm.key_pairs_location,
                                                                          reservation_id=self.reservation.reservation_id)
        self.crypto_service.encrypt.assert_called_once_with(access_key)
        self.assertEqual(results[0].actionId, action.id)
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].infoMessage, 'PrepareNetwork finished successfully')
        self.assertEqual(results[0].errorMessage, '')
        self.assertEqual(results[0].access_key, crypto_dto.encrypted_input)
        self.assertEqual(results[0].secret_key, crypto_dto.encrypted_asymmetric_key)
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

    def test_prepare_conn_command_fault_res(self):
        action = NetworkAction()
        action.id = "1234"
        action.connection_params = PrepareNetworkParams()
        cancellation_context = Mock()

        results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                         ec2_session=self.ec2_session,
                                                         s3_session=self.s3_session,
                                                         reservation=self.reservation,
                                                         aws_ec2_datamodel=self.aws_dm,
                                                         actions=[action],
                                                         cancellation_context=cancellation_context,
                                                         logger=Mock())

        self.assertEqual(results[0].actionId, action.id)
        self.assertFalse(results[0].success)
        self.assertEqual(results[0].infoMessage, '')
        self.assertIsNotNone(results[0].errorMessage)

    def test_create_key_pair(self):
        key_pair_service = Mock()
        key_pair_service.load_key_pair_by_name = Mock(return_value=None)
        prepare_conn = PrepareConnectivityOperation(self.vpc_serv, self.sg_serv, key_pair_service, self.tag_service,
                                                    self.route_table_service, self.crypto_service, self.cancellation_service)
        key_pair = Mock()
        key_pair_service.create_key_pair = Mock(return_value=key_pair)

        access_key = prepare_conn._get_or_create_key_pair(self.ec2_session, self.s3_session, 'bucket', 'res_id')

        self.assertTrue(key_pair_service.load_key_pair_by_name.called_with(self.s3_session, 'bucket', 'res_id'))
        self.assertTrue(key_pair_service.create_key_pair.called_with(self.ec2_session,
                                                                     self.s3_session,
                                                                     'bucket',
                                                                     'res_id'))
        self.assertEquals(access_key, key_pair.key_material)

    def test_get_or_create_security_group(self):
        sg_name = Mock()
        sg = Mock()
        vpc = Mock()
        management_sg_id = Mock()
        security_group_service = Mock()
        security_group_service.get_security_group_name = Mock(return_value=sg_name)
        security_group_service.get_security_group_by_name = Mock(return_value=None)
        security_group_service.create_security_group = Mock(return_value=sg)

        prepare_conn = PrepareConnectivityOperation(self.vpc_serv, security_group_service, self.key_pair_serv,
                                                    self.tag_service, self.route_table_service,
                                                    self.crypto_service, self.cancellation_service)

        res = prepare_conn._get_or_create_security_group(self.ec2_session, self.reservation, vpc, management_sg_id)

        self.assertTrue(security_group_service.get_security_group_name.called_with('reservation'))
        self.assertTrue(security_group_service.get_security_group_by_name.called_with(vpc, sg_name))
        self.assertTrue(security_group_service.create_security_group.called_with(self.ec2_session, vpc.id, sg_name))
        self.assertEqual(sg, res)

    def test_get_or_create_vpc(self):
        cidr = Mock()
        reservation_id = Mock()
        vpc = Mock()
        vpc_service = Mock()
        vpc_service.find_vpc_for_reservation = Mock(return_value=None)
        vpc_service.create_vpc_for_reservation = Mock(return_value=vpc)

        prepare_conn = PrepareConnectivityOperation(vpc_service, self.sg_serv, self.key_pair_serv, self.tag_service,
                                                    self.route_table_service, self.crypto_service,
                                                    self.cancellation_service)

        res = prepare_conn._get_or_create_vpc(cidr, self.ec2_session, reservation_id)

        self.assertTrue(vpc_service.find_vpc_for_reservation.called_with(self.ec2_session, reservation_id))
        self.assertTrue(vpc_service.create_vpc_for_reservation.called_with(self.ec2_session, reservation_id, cidr))
        self.assertEqual(vpc, res)

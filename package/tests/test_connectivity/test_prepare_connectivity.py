from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareConnectivityOperation


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

        self.prepare_conn = PrepareConnectivityOperation(self.vpc_serv, self.sg_serv, self.key_pair_serv,
                                                         self.tag_service, self.route_table_service,
                                                         self.crypto_service)

    def test_prepare_conn_command(self):
        # Arrange
        request = DeployDataHolder({"actions": [
            {"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356", "actionTarget": None, "customActionAttributes": [
                {"attributeName": "Network", "attributeValue": "10.0.0.0/24", "type": "customAttribute"}],
             "type": "prepareNetwork"}]})
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
                                                         request=request,
                                                         logger=Mock())

        self.prepare_conn._get_or_create_key_pair.assert_called_once_with(ec2_session=self.ec2_session,
                                                                          s3_session=self.s3_session,
                                                                          bucket=self.aws_dm.key_pairs_location,
                                                                          reservation_id=self.reservation.reservation_id)
        self.crypto_service.encrypt.assert_called_once_with(access_key)
        self.assertEqual(request.actions[0].actionId, results[0].actionId)
        self.assertEqual(results[0].type, 'PrepareNetwork')
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].infoMessage, 'PrepareConnectivity finished successfully')
        self.assertEqual(results[0].errorMessage, '')
        self.assertEqual(results[0].access_key, crypto_dto.encrypted_input)
        self.assertEqual(results[0].secret_key, crypto_dto.encrypted_asymmetric_key)

    def test_prepare_conn_command_no_management_vpc(self):
        request = Mock()
        aws_dm = Mock()
        aws_dm.aws_management_vpc_id = None
        self.assertRaises(ValueError,
                          self.prepare_conn.prepare_connectivity,
                          self.ec2_client,
                          self.ec2_session,
                          self.s3_session,
                          self.reservation,
                          aws_dm,
                          request,
                          Mock())

    def test_prepare_conn_command_fault_res(self):
        request = DeployDataHolder({"actions": [
            {"actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356", "actionTarget": None,
             "type": "prepareNetwork"}]})

        results = self.prepare_conn.prepare_connectivity(ec2_client=self.ec2_client,
                                                         ec2_session=self.ec2_session,
                                                         s3_session=self.s3_session,
                                                         reservation=self.reservation,
                                                         aws_ec2_datamodel=self.aws_dm,
                                                         request=request,
                                                         logger=Mock())

        self.assertEqual(request.actions[0].actionId, results[0].actionId)
        self.assertEqual(results[0].type, 'PrepareNetwork')
        self.assertFalse(results[0].success)
        self.assertEqual(results[0].infoMessage, '')
        self.assertIsNotNone(results[0].errorMessage)

    def test_create_key_pair(self):
        key_pair_service = Mock()
        key_pair_service.load_key_pair_by_name = Mock(return_value=None)
        prepare_conn = PrepareConnectivityOperation(self.vpc_serv, self.sg_serv, key_pair_service, self.tag_service,
                                                    self.route_table_service, self.crypto_service)
        key_pair = Mock()
        key_pair_service.create_key_pair = Mock(return_value=key_pair)

        access_key = prepare_conn._get_or_create_key_pair(self.ec2_session, self.s3_session, 'bucket', 'res_id')

        self.assertTrue(key_pair_service.load_key_pair_by_name.called_with(self.s3_session, 'bucket', 'res_id'))
        self.assertTrue(key_pair_service.create_key_pair.called_with(self.ec2_session,
                                                                     self.s3_session,
                                                                     'bucket',
                                                                     'res_id'))
        self.assertEquals(access_key, key_pair.key_material)

    def test_extract_cidr(self):
        action1 = DeployDataHolder({
            "customActionAttributes": [{
                "attributeName": "Network",
                "attributeValue": "10.0.0.0/24",
                "type": "customAttribute"}],
            "type": "prepareNetwork"})

        cidr = self.prepare_conn._extract_cidr(action1)
        self.assertEqual(cidr, '10.0.0.0/24')

        action2 = DeployDataHolder({
            "customActionAttributes": [
                {
                    "attributeName": "Network",
                    "attributeValue": "10.0.0.0/24",
                    "type": "customAttribute"
                },
                {
                    "attributeName": "Network",
                    "attributeValue": "10.0.0.0/24",
                    "type": "customAttribute"
                }
            ],
            "type": "prepareNetwork"})

        self.assertRaises(ValueError, self.prepare_conn._extract_cidr, action2)

        action3 = DeployDataHolder({
            "customActionAttributes": [
            ],
            "type": "prepareNetwork"})

        self.assertRaises(ValueError, self.prepare_conn._extract_cidr, action3)

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
                                                    self.crypto_service)

        res = prepare_conn._get_or_create_security_group(self.ec2_session, self.reservation, vpc, management_sg_id)

        self.assertTrue(security_group_service.get_security_group_name.called_with('reservation'))
        self.assertTrue(security_group_service.get_security_group_by_name.called_with(vpc, sg_name))
        self.assertTrue(security_group_service.create_security_group.called_with(self.ec2_session, vpc.id, sg_name))
        self.assertEqual(sg, res)

    def test_get_or_create_vpc(self):
        action = Mock()
        reservation_id = Mock()
        vpc = Mock()
        vpc_service = Mock()
        vpc_service.find_vpc_for_reservation = Mock(return_value=None)
        vpc_service.create_vpc_for_reservation = Mock(return_value=vpc)

        prepare_conn = PrepareConnectivityOperation(vpc_service, self.sg_serv, self.key_pair_serv, self.tag_service,
                                                    self.route_table_service, self.crypto_service)
        cidr = Mock()
        prepare_conn._extract_cidr = Mock(return_value=cidr)
        res = prepare_conn._get_or_create_vpc(action, self.ec2_session, reservation_id)

        self.assertTrue(vpc_service.find_vpc_for_reservation.called_with(self.ec2_session, reservation_id))
        self.assertTrue(vpc_service.create_vpc_for_reservation.called_with(self.ec2_session, reservation_id, cidr))
        self.assertTrue(prepare_conn._extract_cidr.called_with(action))
        self.assertEqual(vpc, res)

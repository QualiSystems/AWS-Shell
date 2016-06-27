from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService


class TestKeyPair(TestCase):
    def setUp(self):
        self.s3_service = Mock()
        self.s3_session = Mock()
        self.ec2_session = Mock()
        self.bucket_name = Mock()
        self.reservation_id = 'id'
        self.key_pair_serv = KeyPairService(self.s3_service)

    def test_create_key_pair(self):
        key = \
            self.key_pair_serv.create_key_pair(self.ec2_session, self.s3_session, self.bucket_name, self.reservation_id)

        self.assertTrue(self.ec2_session.create_key_pair.called_with(
            self.key_pair_serv._get_reservation_key_name(self.reservation_id)))
        self.assertTrue(
            self.s3_service.put_key.called_with(self.s3_session,
                                                self.bucket_name,
                                                self.key_pair_serv._get_s3_key_location(self.reservation_id),
                                                self.ec2_session.create_key_pair()))
        self.assertEqual(key, self.ec2_session.create_key_pair())

    def test_get_key_for_reservation(self):
        key = \
            self.key_pair_serv.get_key_for_reservation(self.s3_session, self.bucket_name, self.reservation_id)

        self.assertTrue(
            self.s3_service.get_key.called_with(self.s3_session,
                                                self.bucket_name,
                                                self.key_pair_serv._get_s3_key_location(self.reservation_id)))
        self.assertEqual(key, self.key_pair_serv._get_s3_key_location(self.reservation_id))

    def test_get_key_for_reservation_not_found(self):
        s3_se = Mock()
        s3_se.get_key = Mock(return_value=None)
        key_pair_serv = KeyPairService(s3_se)
        key = \
            key_pair_serv.get_key_for_reservation(self.s3_session, self.bucket_name, self.reservation_id)

        self.assertIsNone(key)

    def test_load_key_pair_by_name(self):
        key = \
            self.key_pair_serv.load_key_pair_by_name(self.s3_session, self.bucket_name, self.reservation_id)

        self.assertTrue(self.s3_service.get_key.called_with(
            self.s3_session,
            self.bucket_name,
            self.key_pair_serv._get_s3_key_location(self.reservation_id)))

        self.assertTrue(self.s3_service.get_body_of_object.called_with(
            self.s3_service.get_key))

        self.assertEqual(key, self.s3_service.get_body_of_object())

    def test_load_key_pair_by_name_not_found(self):
        s3_se = Mock()
        s3_se.get_key = Mock(return_value=None)
        key_pair_serv = KeyPairService(s3_se)
        key = \
            key_pair_serv.load_key_pair_by_name(self.s3_session, self.bucket_name, self.reservation_id)

        self.assertIsNone(key)


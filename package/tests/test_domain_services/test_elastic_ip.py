from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.elastic_ip import ElasticIpService


class TestElasticIpService(TestCase):
    def setUp(self):
        self.elastic_ip_service = ElasticIpService()

    def test_allocate_elastic_address(self):
        ec2_client = Mock()
        result={'PublicIp': 'string'}
        ec2_client.allocate_address = Mock(return_value=result)
        res = self.elastic_ip_service.allocate_elastic_address(ec2_client)
        self.assertTrue(ec2_client.allocate_address.called)

    def test_find_and_release_elastic_address(self):
        # arrange
        ec2_session = Mock()
        elastic_ip = "xxx"
        vpc_address = Mock()
        ec2_session.vpc_addresses.filter = Mock(return_value=[vpc_address])

        # act
        self.elastic_ip_service.find_and_release_elastic_address(ec2_session=ec2_session, elastic_ip=elastic_ip)

        # assert
        ec2_session.vpc_addresses.filter.assert_called_once_with(PublicIps=[elastic_ip])
        vpc_address.release.assert_called_once()

    def test_find_and_release_elastic_address_failed_to_find_ip(self):
        # arrange
        ec2_session = Mock()
        elastic_ip = "xxx"
        ec2_session.vpc_addresses.filter = Mock(return_value=[])

        # act & assert
        with self.assertRaisesRegexp(ValueError, "Failed to find elastic ip xxx"):
            self.elastic_ip_service.find_and_release_elastic_address(ec2_session=ec2_session, elastic_ip=elastic_ip)

    def test_release_elastic_address(self):
        vpc_address = Mock()
        res = self.elastic_ip_service.release_elastic_address(vpc_address)
        self.assertTrue(vpc_address.release.called)



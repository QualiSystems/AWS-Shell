from unittest import TestCase

from mock import Mock, MagicMock, call, patch

from cloudshell.cp.aws.domain.services.ec2.elastic_ip import ElasticIpService
from cloudshell.cp.aws.models.network_actions_models import DeployNetworkingResultModel
from cloudshell.cp.core.models import PrepareSubnetParams, ConnectSubnet, ConnectToSubnetParams


class TestElasticIpService(TestCase):
    def setUp(self):
        self.elastic_ip_service = ElasticIpService()

    def test_allocate_elastic_address(self):
        ec2_client = Mock()
        result = {'PublicIp': 'string'}
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

    def test_associate_elastic_ip_to_network_interface(self):
        # arrange
        ec2_session = Mock()
        ec2_session.vpc_addresses = Mock()
        vpc_address = Mock()
        ec2_session.vpc_addresses.filter = Mock(return_value=[vpc_address])
        interface_id = Mock()
        elastic_ip = Mock()

        # act
        self.elastic_ip_service.associate_elastic_ip_to_network_interface(ec2_session=ec2_session,
                                                                          interface_id=interface_id,
                                                                          elastic_ip=elastic_ip)

        # assert
        vpc_address.associate.assert_called_once_with(NetworkInterfaceId=interface_id, AllowReassociation=False)

    def test_associate_elastic_ip_to_network_interface_raises_when_no_ip_found(self):
        # arrange
        ec2_session = Mock()
        ec2_session.vpc_addresses = Mock()
        ec2_session.vpc_addresses.filter = Mock(return_value=[])
        interface_id = Mock()
        elastic_ip = Mock()

        # act
        with self.assertRaisesRegexp(ValueError, "Failed to find elastic ip"):
            self.elastic_ip_service.associate_elastic_ip_to_network_interface(ec2_session=ec2_session,
                                                                              interface_id=interface_id,
                                                                              elastic_ip=elastic_ip)

    def test_associate_elastic_ip_to_instance(self):
        # arrange
        ec2_session = Mock()
        ec2_session.vpc_addresses = Mock()
        vpc_address = Mock()
        ec2_session.vpc_addresses.filter = Mock(return_value=[vpc_address])
        instance = Mock()
        elastic_ip = Mock()

        # act
        self.elastic_ip_service.associate_elastic_ip_to_instance(ec2_session=ec2_session,
                                                                 instance=instance,
                                                                 elastic_ip=elastic_ip)

    def test_associate_elastic_ip_to_instance_raises_when_no_ip_found(self):
        # arrange
        ec2_session = Mock()
        ec2_session.vpc_addresses = Mock()
        ec2_session.vpc_addresses.filter = Mock(return_value=[])
        instance = Mock()
        elastic_ip = Mock()

        # act
        with self.assertRaisesRegexp(ValueError, "Failed to find elastic ip"):
            self.elastic_ip_service.associate_elastic_ip_to_instance(ec2_session=ec2_session,
                                                                     instance=instance,
                                                                     elastic_ip=elastic_ip)

    def test_set_elastic_ips_single_subnet(self):
        # arrange
        ec2_session = Mock()
        ec2_client = Mock()
        instance = Mock()
        ami_deployment_model = Mock()
        network_actions=Mock()
        network_config_result_mock = Mock()
        network_config_results = [network_config_result_mock]

        elastic_ip_service = ElasticIpService()

        elastic_ip_service._is_single_subnet_mode = Mock(return_value=True)
        allocated_elastic_ip = Mock()
        elastic_ip_service.allocate_elastic_address = Mock(return_value=allocated_elastic_ip)
        elastic_ip_service.associate_elastic_ip_to_instance = Mock()

        # act
        elastic_ip_service.set_elastic_ips(ec2_session=ec2_session,
                                           ec2_client=ec2_client,
                                           instance=instance,
                                           ami_deployment_model=ami_deployment_model,
                                           network_actions=network_actions,
                                           network_config_results=network_config_results,
                                           logger=Mock())

        # assert
        elastic_ip_service.allocate_elastic_address.assert_called_once_with(ec2_client)
        self.assertEquals(network_config_result_mock.public_ip, allocated_elastic_ip)
        elastic_ip_service.associate_elastic_ip_to_instance.assert_called_once_with(
            ec2_session, instance, allocated_elastic_ip
        )
        instance.network_interfaces_attribute.all.assert_not_called()

    def test_set_elastic_ips_multiple_subnets_with_2_public_1_private(self):
        # arrange
        ec2_session = Mock()
        ec2_client = Mock()
        instance = Mock()
        instance.network_interfaces_attribute = [
            {"Attachment": {"DeviceIndex": 0}, "NetworkInterfaceId": "netif0"},
            {"Attachment": {"DeviceIndex": 1}, "NetworkInterfaceId": "netif1"},
            {"Attachment": {"DeviceIndex": 2}, "NetworkInterfaceId": "netif2"},
            {"Attachment": {"DeviceIndex": 3}, "NetworkInterfaceId": "netif3"}]

        action1 = Mock()
        action1.actionParams = Mock(spec=ConnectToSubnetParams)
        action1.actionParams.isPublic = True # public subnet

        action2 = Mock()
        action2.actionParams = Mock(spec=ConnectToSubnetParams)
        action2.actionParams.isPublic = False  # private subnet

        action3 = Mock()
        action3.actionParams = Mock(spec=ConnectToSubnetParams)
        action3.actionParams.isPublic = True  # public subnet

        ami_deployment_model = Mock()
        ami_deployment_model.network_configurations = [action1, action2, action3]

        network_actions = [action1, action2, action3]

        result_mock1 = Mock(spec=DeployNetworkingResultModel, action_id=action1.actionId, device_index=0)
        result_mock2 = Mock(spec=DeployNetworkingResultModel, action_id=action2.actionId, device_index=1)
        result_mock3 = Mock(spec=DeployNetworkingResultModel, action_id=action3.actionId, device_index=2)
        network_config_results = [result_mock1, result_mock2, result_mock3]

        elastic_ip_service = ElasticIpService()
        elastic_ip_service._is_single_subnet_mode = Mock(return_value=False)
        allocated_elastic_ip = Mock()
        elastic_ip_service.allocate_elastic_address = Mock(return_value=allocated_elastic_ip)
        elastic_ip_service.associate_elastic_ip_to_network_interface = Mock()

        # act
        elastic_ip_service.set_elastic_ips(ec2_session=ec2_session,
                                           ec2_client=ec2_client,
                                           instance=instance,
                                           ami_deployment_model=ami_deployment_model,
                                           network_actions=network_actions,
                                           network_config_results=network_config_results,
                                           logger=Mock())

        # assert
        #self.assertEquals(instance.network_interfaces_attribute.call_count, 2)

        self.assertEquals(elastic_ip_service.allocate_elastic_address.call_count, 2)
        self.assertEquals(elastic_ip_service.associate_elastic_ip_to_network_interface.call_count, 2)
        elastic_ip_service.associate_elastic_ip_to_network_interface.assert_has_calls(
                [call(ec2_session, "netif0", allocated_elastic_ip),
                 call(ec2_session, "netif2", allocated_elastic_ip)])
        self.assertEquals(result_mock1.public_ip, allocated_elastic_ip)
        self.assertEquals(result_mock3.public_ip, allocated_elastic_ip)
        self.assertFalse(hasattr(result_mock2, 'public_ip'))  # to make sure public_ip wasnt set on result_mock2

    def test_is_single_subnet_true(self):
        # arrange
        network_actions =None

        # act
        result = self.elastic_ip_service._is_single_subnet_mode(network_actions=network_actions)

        # assert
        self.assertTrue(result)

    def test_is_single_subnet_false(self):
        # arrange
        network_actions = Mock()


        # act
        result = self.elastic_ip_service._is_single_subnet_mode(network_actions=network_actions)

        # assert
        self.assertFalse(result)

    def test__create_and_associate_elastic_ip_interface_id(self):
        interface_id = 'interface id'
        ec2_client = Mock()
        ec2_session = Mock()
        expected_ip = Mock()
        vpc_address = Mock()
        ec2_client.allocate_address.return_value = {'PublicIp': expected_ip}
        ec2_session.vpc_addresses.filter.return_value = [vpc_address]

        ip = self.elastic_ip_service._create_and_associate_elastic_ip(
            ec2_client, ec2_session, interface_id
        )

        self.assertEquals(ip, expected_ip)
        ec2_client.allocate_address.assert_called_once_with(Domain='vpc')
        ec2_session.vpc_addresses.filter.assert_called_once_with(PublicIps=[expected_ip])
        vpc_address.associate.assert_called_once_with(
            NetworkInterfaceId=interface_id, AllowReassociation=False
        )

    def test__create_and_associate_elastic_ip_instance(self):
        instance = Mock()
        ec2_client = Mock()
        ec2_session = Mock()
        expected_ip = Mock()
        vpc_address = Mock()
        ec2_client.allocate_address.return_value = {'PublicIp': expected_ip}
        ec2_session.vpc_addresses.filter.return_value = [vpc_address]

        ip = self.elastic_ip_service._create_and_associate_elastic_ip(
            ec2_client, ec2_session, instance
        )

        self.assertEquals(ip, expected_ip)
        ec2_client.allocate_address.assert_called_once_with(Domain='vpc')
        ec2_session.vpc_addresses.filter.assert_called_once_with(PublicIps=[expected_ip])
        vpc_address.associate.assert_called_once_with(
            InstanceId=instance.id, AllowReassociation=False
        )

    def test__create_and_associate_elastic_ip_failed_first_time(self):
        interface_id = 'interface id'
        ec2_client = MagicMock()
        ec2_session = Mock()
        associate_elastic_ip_to_network_interface = Mock(
            side_effect=[Exception, Exception, None]
        )
        self.elastic_ip_service.associate_elastic_ip_to_network_interface = (
            associate_elastic_ip_to_network_interface
        )
        find_and_release_elastic_address = Mock()
        self.elastic_ip_service.find_and_release_elastic_address = (
            find_and_release_elastic_address
        )
        allocate_elastic_address = Mock()
        self.elastic_ip_service.allocate_elastic_address = allocate_elastic_address

        with patch('time.sleep', Mock()):
            self.elastic_ip_service._create_and_associate_elastic_ip(
                ec2_client, ec2_session, interface_id
            )

        self.assertEquals(allocate_elastic_address.call_count, 3)
        self.assertEquals(find_and_release_elastic_address.call_count, 2)
        self.assertEquals(associate_elastic_ip_to_network_interface.call_count, 3)

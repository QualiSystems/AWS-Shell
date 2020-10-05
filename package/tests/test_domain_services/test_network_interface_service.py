from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.services.ec2.network_interface import NetworkInterfaceService


class TestNetworkInterfaceService(TestCase):
    def setUp(self):
        self.subnet_service = Mock()
        self.network_interface_service = NetworkInterfaceService(subnet_service=self.subnet_service)

    def test_build_network_interface_dto(self):
        # arrange
        subnet_id = Mock()
        device_index = Mock()
        groups = MagicMock()
        public_ip = Mock()

        # act
        dto = self.network_interface_service.build_network_interface_dto(subnet_id=subnet_id,
                                                                         device_index=device_index,
                                                                         groups=groups,
                                                                         public_ip=public_ip)

        # assert
        self.assertEquals(dto['SubnetId'], subnet_id)
        self.assertEquals(dto['DeviceIndex'], device_index)
        self.assertEquals(dto['Groups'], groups)
        self.assertEquals(dto['AssociatePublicIpAddress'], public_ip)

    def test_build_network_interface_dto_no_public_ip(self):
        # arrange
        subnet_id = Mock()
        device_index = Mock()
        groups = MagicMock()

        # act
        dto = self.network_interface_service.build_network_interface_dto(subnet_id=subnet_id,
                                                                         device_index=device_index,
                                                                         groups=groups)

        # assert
        self.assertEquals(dto['SubnetId'], subnet_id)
        self.assertEquals(dto['DeviceIndex'], device_index)
        self.assertEquals(dto['Groups'], groups)
        self.assertTrue('AssociatePublicIpAddress' not in dto)

    def test_get_network_interface_for_single_subnet_mode(self):
        # arrange
        self.network_interface_service.build_network_interface_dto = Mock()
        add_public_ip = Mock()
        security_group_ids = Mock()
        vpc = Mock()
        subnet_id_mock = Mock()
        self.subnet_service.get_first_subnet_from_vpc = Mock(return_value=Mock(subnet_id=subnet_id_mock))

        # act
        result = self.network_interface_service.get_network_interface_for_single_subnet_mode(
                add_public_ip=add_public_ip,
                security_group_ids=security_group_ids,
                vpc=vpc)

        # assert
        self.network_interface_service.build_network_interface_dto.assert_called_once_with(
                subnet_id=subnet_id_mock,
                device_index=0,
                groups=security_group_ids,
                public_ip=add_public_ip,
                private_ip=None)

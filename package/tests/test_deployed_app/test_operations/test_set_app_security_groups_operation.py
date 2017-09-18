from unittest import TestCase

from cloudshell.shell.core.context import ReservationContextDetails
from mock import Mock

from cloudshell.cp.aws.domain.deployed_app.operations.set_app_security_groups import SetAppSecurityGroupsOperation
from cloudshell.cp.aws.models.app_security_groups_model import AppSecurityGroupModel, DeployedApp, VmDetails, \
    SecurityGroupConfiguration
from cloudshell.cp.aws.models.port_data import PortData
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class TestSetAppSecurityGroupsOperation(TestCase):
    def setUp(self):
        self.instance_service = Mock()
        self.instance = Mock()

        self.nic = Mock()
        self.nic.subnet_id = "subnet_id"

        self.instance.vpc_id = "vpc_id"
        self.instance.network_interfaces = [self.nic]
        self.instance_service.get_active_instance_by_id = Mock(return_value=self.instance)
        self.tag_service = Mock()
        self.security_group_service = Mock()

        self.operation = SetAppSecurityGroupsOperation(instance_service=self.instance_service,
                                                       tag_service=self.tag_service,
                                                       security_group_service=self.security_group_service)
        self.app_models = [self._init_app_model()]
        self.reservation_model = self._init_reservation_model()
        self.logger = Mock()
        self.ec2_session = Mock()

        self.security_group_service.get_or_create_custom_security_group = Mock()

    @staticmethod
    def _init_reservation_model():
        reservation_context = ReservationContextDetails()
        reservation_model = ReservationModel(reservation_context)
        reservation_model.reservation_id = "77bf1176-25d2-4dd0-ac58-05f8aee534a5"
        return reservation_model

    @staticmethod
    def _init_app_model():
        app_model = AppSecurityGroupModel()

        app_model.deployed_app = DeployedApp()
        app_model.deployed_app.name = "tested app"
        app_model.deployed_app.vm_details = VmDetails()
        app_model.deployed_app.vm_details.uid = "uid"

        configuration = SecurityGroupConfiguration()
        configuration.subnet_id = "subnet_id"
        port_data = PortData('1', '2', 'tcp', '0.0.0.0/0')
        configuration.rules = [port_data]
        app_model.security_group_configurations = [configuration]

        return app_model

    def test_set_apps_security_groups(self):
        result = self.operation.set_apps_security_groups(reservation=self.reservation_model,
                                                         logger=self.logger,
                                                         app_security_group_models=self.app_models,
                                                         ec2_session=self.ec2_session)

        self.assertTrue(result[0].appName == "tested app")

        self.security_group_service.get_or_create_custom_security_group.assert_called_once_with(
            ec2_session=self.ec2_session,
            logger=self.logger,
            network_interface=self.nic,
            reservation=self.reservation_model,
            vpc_id="vpc_id"
        )

        self.security_group_service.set_security_group_rules.assert_called_once()

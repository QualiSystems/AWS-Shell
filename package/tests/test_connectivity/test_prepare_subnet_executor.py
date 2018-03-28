from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.conncetivity.operations.prepare_subnet_executor import PrepareSubnetExecutor
from cloudshell.cp.aws.domain.services.ec2.tags import TagService, TagNames
from cloudshell.cp.aws.models.network_actions_models import PrepareNetworkParams, NetworkAction, PrepareSubnetParams


class TestPrepareSandboxInfra(TestCase):
    def setUp(self):
        self.ec2_client = Mock()
        self.ec2_session = Mock()
        self.logger = Mock()
        self.cancellation_context = Mock()
        self.aws_ec2_datamodel = Mock()
        self.reservation = Mock()
        self.cancellation_service = Mock()
        self.vpc_service = Mock()
        self.subnet_service = Mock()
        self.tag_service = Mock()
        self.subnet_waiter = Mock()

        self.executor = PrepareSubnetExecutor(self.cancellation_service, self.vpc_service, self.subnet_service,
                                              self.tag_service, self.subnet_waiter, self.reservation,
                                              self.aws_ec2_datamodel, self.cancellation_context, self.logger,
                                              self.ec2_session, self.ec2_client)

    def test_execute_with_wrong_action_type(self):
        # Arrange
        actions = [NetworkAction(id="1", connection_params=PrepareNetworkParams())]
        # Act
        with self.assertRaises(Exception) as error:
            self.executor.execute(actions)
        # Assert
        self.assertEqual(error.exception.message, "Not all actions are PrepareSubnetActions")

    def test_execute_with_no_vpc(self):
        # Arrange
        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams())]
        self.vpc_service.find_vpc_for_reservation = Mock(return_value=None)
        self.vpc_service.get_active_vpcs_count = Mock(return_value=None)

        self.reservation.reservation_id = "123"
        # Act
        with self.assertRaises(Exception) as error:
            self.executor.execute(actions)
        # Assert
        self.assertEqual(error.exception.message, "VPC for reservation 123 not found.")

    def test_execute_gets_existing_subnet_and_no_wait(self):
        # Arrange
        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams(cidr="1.2.3.4/24"))]
        subnet = Mock()
        subnet.subnet_id = "123"
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=subnet)
        # Act
        result = self.executor.execute(actions)[0]
        # Assert
        self.assertEqual(result.subnetId, "123")
        self.subnet_waiter.wait.assert_not_called()

    def test_execute_creates_new_subnet_and_wait(self):
        # Arrange
        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams(cidr="1.2.3.4/24"))]
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=None)
        subnet = Mock()
        subnet.subnet_id = "456"
        self.subnet_service.create_subnet_nowait = Mock(return_value=subnet)
        # Act
        result = self.executor.execute(actions)[0]
        # Assert
        self.assertEqual(result.subnetId, "456")
        self.subnet_waiter.wait.assert_called_once()

    def test_execute_sets_tags(self):
        # Arrange
        def return_public_tag_with_value(*args, **kwargs):
            return {'Key': TagNames.IsPublic, 'Value': args[0]}

        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams(cidr="1.2.3.4/24", alias="MySubnet"))]
        self.reservation.reservation_id = "123"
        subnet = Mock()
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=subnet)
        is_public_tag = Mock()
        self.tag_service.get_is_public_tag = Mock(return_value=is_public_tag)
        default_tags = [Mock()]
        self.tag_service.get_default_tags = Mock(return_value=default_tags)

        # Act
        self.executor.execute(actions)

        # Assert
        default_tags.append(is_public_tag)
        self.tag_service.set_ec2_resource_tags.assert_called_once_with(subnet, default_tags)

    def test_execute_sets_private_subnet_to_private_routing_table(self):
        # Arrange
        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams(cidr="1.2.3.4/24", is_public=False))]
        # Act
        self.executor.execute(actions)
        # Assert
        self.subnet_service.set_subnet_route_table.assert_called_once()

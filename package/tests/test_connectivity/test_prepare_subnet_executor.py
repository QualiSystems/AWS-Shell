from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.conncetivity.operations.prepare_subnet_executor import PrepareSubnetExecutor
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.network_actions_models import PrepareNetworkParams, NetworkAction, PrepareSubnetParams
from tests.test_common.test_mock_helper import Any


class TestPrepareConnectivity(TestCase):
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
        self.tag_service = TagService() #Mock()
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
        self.reservation.reservation_id = "123"
        # Act
        with self.assertRaises(Exception) as error:
            self.executor.execute(actions)
        # Assert
        self.assertEqual(error.exception.message, "Vpc for reservation 123 not found.")

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
        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams(cidr="1.2.3.4/24", alias="MySubnet"))]
        self.reservation.reservation_id = "123"
        subnet = Mock()
        self.subnet_service.get_first_or_none_subnet_from_vpc = Mock(return_value=subnet)
        # Act
        self.executor.execute(actions)
        # Assert
        subnet.create_tags.assert_called_once_with(Tags=Any(lambda tags:
            any(x["Key"]=="Name" and x["Value"]=="MySubnet Reservation: 123" for x in tags) and
            any(x["Key"]=="IsPublic" and x["Value"]=="True" for x in tags)))

    def test_execute_sets_private_subnet_to_private_routing_table(self):
        # Arrange
        actions = [NetworkAction(id="1", connection_params=PrepareSubnetParams(cidr="1.2.3.4/24", is_public=False))]
        # Act
        self.executor.execute(actions)
        # Assert
        self.subnet_service.set_subnet_route_table.assert_called_once()
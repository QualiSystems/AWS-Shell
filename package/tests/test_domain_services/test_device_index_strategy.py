from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.strategy.device_index import AllocateMissingValuesDeviceIndexStrategy
from cloudshell.cp.aws.models.network_actions_models import NetworkAction, SubnetActionParams


class TestAllocateMissingValuesDeviceIndexStrategy(TestCase):
    def setUp(self):
        self.strategy = AllocateMissingValuesDeviceIndexStrategy()

    def test_strategy_allocates_missing_values_successfully(self):
        # arrange
        action1 = Mock(spec=NetworkAction)
        action1.connection_params = Mock(spec=SubnetActionParams)
        action1.connection_params.device_index = None

        action2 = Mock(spec=NetworkAction)
        action2.connection_params = Mock(spec=SubnetActionParams)
        action2.connection_params.device_index = 1

        action3 = Mock(spec=NetworkAction)
        action3.connection_params = Mock(spec=SubnetActionParams)
        action3.connection_params.device_index = None

        action4 = Mock(spec=NetworkAction)
        action4.connection_params = Mock(spec=SubnetActionParams)
        action4.connection_params.device_index = 3

        actions = [action1, action2, action3, action4]

        # act
        self.strategy.apply(actions)

        # assert
        # the order in witch the strategy assign device indexes is not guaranteed
        self.assertTrue(action1.connection_params.device_index in [0, 2])
        self.assertTrue(action3.connection_params.device_index in [0, 2])
        self.assertTrue(action1.connection_params.device_index != action3.connection_params.device_index)

    def test_strategy_allocates_missing_values_raises_on_device_index_duplicates(self):
        # arrange
        action1 = Mock(spec=NetworkAction)
        action1.connection_params = Mock(spec=SubnetActionParams)
        action1.connection_params.device_index = 1

        action2 = Mock(spec=NetworkAction)
        action2.connection_params = Mock(spec=SubnetActionParams)
        action2.connection_params.device_index = 1

        action3 = Mock(spec=NetworkAction)
        action3.connection_params = Mock(spec=SubnetActionParams)
        action3.connection_params.device_index = None

        actions = [action1, action2, action3]

        # act & assert
        with self.assertRaisesRegexp(ValueError, "Duplicate 'Requested vNic Name' attribute value found"):
            self.strategy.apply(actions)

    def test_strategy_allocates_missing_values_raises_when_not_continuous(self):
        # arrange
        action1 = Mock(spec=NetworkAction)
        action1.connection_params = Mock(spec=SubnetActionParams)
        action1.connection_params.device_index = 0

        action2 = Mock(spec=NetworkAction)
        action2.connection_params = Mock(spec=SubnetActionParams)
        action2.connection_params.device_index = 4

        action3 = Mock(spec=NetworkAction)
        action3.connection_params = Mock(spec=SubnetActionParams)
        action3.connection_params.device_index = None

        actions = [action1, action2, action3]

        # act & assert
        with self.assertRaisesRegexp(ValueError, "'Requested vNic Name' attribute values are not a continuous list"):
            self.strategy.apply(actions)

    def test_strategy_allocates_missing_values_no_changes_when_not_needed(self):
        # arrange
        action1 = Mock(spec=NetworkAction)
        action1.connection_params = Mock(spec=SubnetActionParams)
        action1.connection_params.device_index = 0

        action2 = Mock(spec=NetworkAction)
        action2.connection_params = Mock(spec=SubnetActionParams)
        action2.connection_params.device_index = 1

        action3 = Mock(spec=NetworkAction)
        action3.connection_params = Mock(spec=SubnetActionParams)
        action3.connection_params.device_index = 2

        actions = [action1, action2, action3]

        # act
        self.strategy.apply(actions)

        # assert
        # the order in witch the strategy assign device indexes is not guaranteed
        self.assertEquals(action1.connection_params.device_index, 0)
        self.assertEquals(action2.connection_params.device_index, 1)
        self.assertEquals(action3.connection_params.device_index, 2)

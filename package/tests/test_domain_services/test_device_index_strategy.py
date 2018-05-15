from unittest import TestCase

from mock import Mock,MagicMock

from cloudshell.cp.aws.domain.services.strategy.device_index import AllocateMissingValuesDeviceIndexStrategy
from cloudshell.cp.core.models import PrepareSubnetParams, PrepareCloudInfra, ConnectToSubnetParams


class TestAllocateMissingValuesDeviceIndexStrategy(TestCase):
    def setUp(self):
        self.strategy = AllocateMissingValuesDeviceIndexStrategy()

    def test_strategy_allocates_missing_values_successfully(self):
        # arrange
        action1 = Mock(spec=PrepareCloudInfra)
        action1.actionParams = Mock(spec=ConnectToSubnetParams)
        action1.actionParams.vnicName = None

        action2 = Mock(spec=PrepareCloudInfra)
        action2.actionParams = Mock(spec=ConnectToSubnetParams)
        action2.actionParams.vnicName = 1

        action3 = Mock(spec=PrepareCloudInfra)
        action3.actionParams = Mock(spec=ConnectToSubnetParams)
        action3.actionParams.vnicName = None

        action4 = Mock(spec=PrepareCloudInfra)
        action4.actionParams = Mock(spec=ConnectToSubnetParams)
        action4.actionParams.vnicName = 3

        actions = [action1, action2, action3, action4]

        # act
        self.strategy.apply(actions)

        # assert
        # the order in witch the strategy assign device indexes is not guaranteed
        self.assertTrue(action1.actionParams.vnicName in [0, 2])
        self.assertTrue(action3.actionParams.vnicName in [0, 2])
        self.assertTrue(action1.actionParams.vnicName != action3.actionParams.vnicName)

    def test_strategy_allocates_missing_values_raises_on_device_index_duplicates(self):
        # arrange
        action1 = Mock(spec=PrepareCloudInfra)
        action1.actionParams = Mock(spec=ConnectToSubnetParams)
        action1.actionParams.vnicName = 1

        action2 = Mock(spec=PrepareCloudInfra)
        action2.actionParams = Mock(spec=ConnectToSubnetParams)
        action2.actionParams.vnicName = 1

        action3 = Mock(spec=PrepareCloudInfra)
        action3.actionParams = Mock(spec=ConnectToSubnetParams)
        action3.actionParams.vnicName = None

        actions = [action1, action2, action3]

        # act & assert
        with self.assertRaisesRegexp(ValueError, "Duplicate 'Requested vNic Name' attribute value found"):
            self.strategy.apply(actions)

    def test_strategy_allocates_missing_values_raises_when_not_continuous(self):
        # arrange
        action1 = Mock(spec=PrepareCloudInfra)
        action1.actionParams = MagicMock(spec=ConnectToSubnetParams)
        action1.actionParams.vnicName = 0

        action2 = Mock(spec=PrepareCloudInfra)
        action2.actionParams = MagicMock(spec=ConnectToSubnetParams)
        action2.actionParams.vnicName = 4

        action3 = Mock(spec=PrepareCloudInfra)
        action3.actionParams = MagicMock(spec=ConnectToSubnetParams)
        action3.actionParams.vnicName = None

        actions = [action1, action2, action3]

        # act & assert
        with self.assertRaisesRegexp(ValueError, "'Requested vNic Name' attribute values are not a continuous list"):
            self.strategy.apply(actions)

    def test_strategy_allocates_missing_values_no_changes_when_not_needed(self):
        # arrange
        action1 = Mock(spec=PrepareCloudInfra)
        action1.actionParams = MagicMock(spec=ConnectToSubnetParams)
        action1.actionParams.vnicName = 0

        action2 = Mock(spec=PrepareCloudInfra)
        action2.actionParams = MagicMock(spec=ConnectToSubnetParams)
        action2.actionParams.vnicName = 1

        action3 = Mock(spec=PrepareCloudInfra)
        action3.actionParams = MagicMock(spec=ConnectToSubnetParams)
        action3.actionParams.vnicName = 2

        actions = [action1, action2, action3]

        # act
        self.strategy.apply(actions)

        # assert
        # the order in witch the strategy assign device indexes is not guaranteed
        self.assertEquals(action1.actionParams.vnicName, 0)
        self.assertEquals(action2.actionParams.vnicName, 1)
        self.assertEquals(action3.actionParams.vnicName, 2)

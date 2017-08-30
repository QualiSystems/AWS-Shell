from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.common.exceptions import CancellationException


class TestRetryHelper(TestCase):
    def setUp(self):
        pass

    def test_exception_on_command_cancellation(self):
        # arrange
        cancellation_service = CommandCancellationService()
        cancellation_context = Mock(is_cancelled=True)

        # act & assert
        with self.assertRaisesRegexp(CancellationException, "Command was cancelled"):
            cancellation_service.check_if_cancelled(cancellation_context)

    def test_exception_with_data_on_command_cancellation(self):
        # arrange
        cancellation_service = CommandCancellationService()
        cancellation_context = Mock(is_cancelled=True)
        data = Mock()

        # act & assert
        with self.assertRaisesRegexp(CancellationException, "Command was cancelled") as assert_exc:
            cancellation_service.check_if_cancelled(cancellation_context, data=data)

        self.assertEquals(assert_exc.exception.data, data)

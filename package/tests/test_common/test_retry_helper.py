from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.common import retry_helper


class TestRetryHelper(TestCase):
    counter = 0

    def setUp(self):
        TestRetryHelper.counter = 0

    def test_retry_action_executed_3_times(self):
        def test_method():
            TestRetryHelper.counter += 1
            if TestRetryHelper.counter != 3:
                raise Exception()

        retry_helper.do_with_retry(test_method)

        assert TestRetryHelper.counter == 3

    def test_retry_action_executes_lambda(self):
        TestRetryHelper.counter = 0

        def test_method():
            TestRetryHelper.counter += 1
            if TestRetryHelper.counter != 2:
                raise Exception()

        mock = Mock()
        mock.reload = Mock(side_effect=test_method)

        retry_helper.do_with_retry(lambda: mock.reload())

        mock.reload.assert_called()
        print "called {0} time/s".format(len(mock.reload.mock_calls))
        assert len(mock.reload.mock_calls) == 2

from unittest import TestCase
from mock import Mock, patch

from cloudshell.cp.aws.domain.services.waiters.instance import InstanceWaiter

instance = Mock()
instance.state = {'Name': ''}


class helper:
    @staticmethod
    def change_to_terminate(a):
        instance.state['Name'] = InstanceWaiter.TERMINATED

    @staticmethod
    def change_to_stopped(a):
        instance.state['Name'] = InstanceWaiter.STOPPED

    @staticmethod
    def change_to_running(a):
        instance.state['Name'] = InstanceWaiter.RUNNING

    @staticmethod
    def change_to_stopping(a):
        instance.state['Name'] = InstanceWaiter.STOPPING

    @staticmethod
    def change_to_pending(a):
        instance.state['Name'] = InstanceWaiter.PENDING


class TestInstanceWaiter(TestCase):
    def setUp(self):
        self.cancellation_service = Mock()
        self.instance_waiter = InstanceWaiter(self.cancellation_service, 1, 0.02)
        self.instance = Mock()
        self.logger = Mock()

    @patch('time.sleep', helper.change_to_stopped)
    def test_waiter(self):
        helper.change_to_running(Mock())
        inst = self.instance_waiter.wait(instance, InstanceWaiter.STOPPED)
        self.assertEqual(inst, instance)
        self.assertEqual(inst.reload.call_count, 1)

    def test_waiter_timeout(self):
        helper.change_to_running(Mock())
        self.assertRaises(Exception, self.instance_waiter.wait, instance, InstanceWaiter.STOPPED)

    @patch('time.sleep', helper.change_to_stopped)
    def test_waiter_multi(self):
        helper.change_to_stopped(Mock())

        instance.state['Name'] = InstanceWaiter.RUNNING

        inst = Mock()
        inst.state = dict()
        inst.state['Name'] = InstanceWaiter.STOPPED

        res = self.instance_waiter.multi_wait([instance, inst], InstanceWaiter.STOPPED)
        self.assertEqual(res, [instance, inst])
        self.assertTrue(instance.reload.call_count, 2)

    @patch('time.sleep', helper.change_to_stopped)
    def test_waiter_multi_with_cancellation(self):
        cancellation_context = Mock()
        helper.change_to_stopped(Mock())

        instance.state['Name'] = InstanceWaiter.RUNNING

        inst = Mock()
        inst.state = dict()
        inst.state['Name'] = InstanceWaiter.STOPPED

        instances = [instance, inst]

        res = self.instance_waiter.multi_wait(instances, InstanceWaiter.STOPPED, cancellation_context)

        self.assertEqual(res, [instance, inst])
        self.assertTrue(instance.reload.call_count, 2)
        self.assertTrue(self.cancellation_service.check_if_cancelled.call_count, 2)
        instance_ids = filter(lambda x: str(x.id), instances)
        self.cancellation_service.check_if_cancelled.assert_called_with(cancellation_context,
                                                                        {'instance_ids': instance_ids})

    def test_waiter_multi_errors(self):
        self.assertRaises(ValueError, self.instance_waiter.multi_wait, [], InstanceWaiter.STOPPED)
        self.assertRaises(ValueError, self.instance_waiter.multi_wait, [Mock], 'blalala')

    @patch('cloudshell.cp.aws.domain.services.waiters.instance.time')
    def test_wait_status_ok(self, time):
        # arrange
        def describe_instance_status_handler(*args, **kwargs):
            result = Mock()
            instance_id_mock = kwargs['InstanceIds'][0]
            if hasattr(instance_id_mock, "called_already") and instance_id_mock.called_already is True:
                result.InstanceStatuses = [{'SystemStatus': {'Status': self.instance_waiter.STATUS_OK},
                                            'InstanceStatus': {'Status': self.instance_waiter.STATUS_OK}}]
            else:
                instance_id_mock.called_already = True
                result.InstanceStatuses = [
                    {'SystemStatus': {'Status': 'initializing'}, 'InstanceStatus': {'Status': 'initializing'}}]

            return result

        time.time.return_value = 0
        ec2_client = Mock()
        ec2_client.describe_instance_status = Mock(side_effect=describe_instance_status_handler)
        instance = Mock()

        # act
        instance_state = self.instance_waiter.wait_status_ok(ec2_client=ec2_client,
                                                             instance=instance,
                                                             logger=self.logger)

        # assert
        self.assertEquals(instance_state['SystemStatus']['Status'], self.instance_waiter.STATUS_OK)
        self.assertEquals(instance_state['InstanceStatus']['Status'], self.instance_waiter.STATUS_OK)

    @patch('cloudshell.cp.aws.domain.services.waiters.instance.time')
    def test_wait_status_ok_raises_impaired_status(self, time):
        # arrange
        def describe_instance_status_handler(*args, **kwargs):
            result = Mock()
            instance_id_mock = kwargs['InstanceIds'][0]
            if hasattr(instance_id_mock, "called_already") and instance_id_mock.called_already is True:
                result.InstanceStatuses = [{'SystemStatus': {'Status': self.instance_waiter.STATUS_IMPAIRED},
                                            'InstanceStatus': {'Status': self.instance_waiter.STATUS_IMPAIRED}}]
            else:
                instance_id_mock.called_already = True
                result.InstanceStatuses = [
                    {'SystemStatus': {'Status': 'initializing'}, 'InstanceStatus': {'Status': 'initializing'}}]

            return result

        time.time.return_value = 0
        ec2_client = Mock()
        ec2_client.describe_instance_status = Mock(side_effect=describe_instance_status_handler)
        instance = Mock()

        # act & assert
        with self.assertRaisesRegexp(ValueError, "Instance status check is not OK.*"):
            instance_state = self.instance_waiter.wait_status_ok(ec2_client=ec2_client,
                                                                 instance=instance,
                                                                 logger=self.logger)


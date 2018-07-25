import time
from multiprocessing import TimeoutError
from cloudshell.shell.core.driver_context import CancellationContext
from retrying import retry


class InstanceWaiter(object):
    PENDING = 'pending'
    RUNNING = 'running'
    SHUTTING_DOWN = 'shutting-down',
    TERMINATED = 'terminated'
    STOPPING = 'stopping'
    STOPPED = 'stopped'
    INSTANCE_STATES = [PENDING,
                       RUNNING,
                       SHUTTING_DOWN,
                       TERMINATED,
                       STOPPING,
                       STOPPED]

    STATUS_OK = 'ok'
    STATUS_IMPAIRED = 'impaired'

    def __init__(self, cancellation_service, delay=15, timeout=10):
        """
        :param delay: the time in seconds between each pull
        :type delay: int
        :param timeout: timeout in minutes until time out exception will raised
        :type timeout: int
        :param cancellation_service:
        :type cancellation_service: cloudshell.cp.aws.domain.common.cancellation_service.CommandCancellationService
        """
        self.delay = delay
        self.timeout = timeout * 60
        self.cancellation_service = cancellation_service

    def wait(self, instance, state, cancellation_context=None):
        """
        Will sync wait for the change of state of the instance
        :param instance:
        :param state:
        :param CancellationContext cancellation_context:
        :return:
        """
        return self.multi_wait([instance], state, cancellation_context)[0]

    def multi_wait(self, instances, state, cancellation_context=None):
        """
        Will sync wait for the change of state of the instance
        :param instances:
        :param str state:
        :param CancellationContext cancellation_context:
        :return:
        """
        if not instances:
            raise ValueError('Instance cannot be null')
        if state not in self.INSTANCE_STATES:
            raise ValueError('Unsupported instance state')

        instance_ids = filter(lambda x: str(x.id), instances)

        start_time = time.time()
        last_item = 0
        while len(instances) - last_item:
            instance = instances[last_item]
            if instance.state['Name'] != state:
                self._reload_instance(instance)
                if time.time() - start_time >= self.timeout:
                    instance = instance or instances[0]
                    raise TimeoutError('Timeout: Waiting for instance to be {0} from'.format(state, instance.state))
                time.sleep(self.delay)
            else:
                last_item += 1

            self.cancellation_service.check_if_cancelled(cancellation_context,
                                                         {'instance_ids': instance_ids})

        return instances

    def wait_status_ok(self, ec2_client, instance, logger, cancellation_context=None):
        """

        :param logging.Logger logger:
        :param instance: Instance
        :param ec2_client: EC2 client
        :param CancellationContext cancellation_context:
        :return:
        """
        if not instance:
            raise ValueError('Instance cannot be null')

        start_time = time.time()

        instance_status = self._get_instance_status(ec2_client, instance)
        while not self._is_instance_status_ok(instance_status):
            if time.time() - start_time >= self.timeout:
                raise TimeoutError('Timeout: Waiting for instance status check to be OK')
            if self._is_instance_status_impaired(instance_status):
                logger.error("Instance status check is not OK: {}".format(instance_status))
                raise ValueError('Instance status check is not OK. Check the log and aws console for more details')

            self.cancellation_service.check_if_cancelled(cancellation_context, {'instance_ids': [instance.id]})

            time.sleep(self.delay)

            instance_status = self._get_instance_status(ec2_client, instance)

        return instance_status

    def _is_instance_status_ok(self, instance_status):
        if not instance_status:
            return False
        return instance_status['SystemStatus']['Status'] == self.STATUS_OK \
               and instance_status['InstanceStatus']['Status'] == self.STATUS_OK

    def _is_instance_status_impaired(self, instance_status):
        if not instance_status:
            return False
        return instance_status['SystemStatus']['Status'] == self.STATUS_IMPAIRED \
               or instance_status['InstanceStatus']['Status'] == self.STATUS_IMPAIRED

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def _get_instance_status(self, ec2_client, instance):
        instance_status = ec2_client.describe_instance_status(InstanceIds=[instance.id], IncludeAllInstances=True)
        if hasattr(instance_status, 'InstanceStatuses'):
            return instance_status.InstanceStatuses[0]
        if 'InstanceStatuses' in instance_status:
            return instance_status['InstanceStatuses'][0]
        return None

    @retry(stop_max_attempt_number=30, wait_fixed=1000)
    def _reload_instance(self, instance):
        instance.reload()

import time
from multiprocessing import TimeoutError
from cloudshell.shell.core.driver_context import CancellationContext


class PasswordWaiter(object):
    def __init__(self, cancellation_service, delay=5, timeout=15):
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

    def wait(self, instance, cancellation_context=None):
        """
        will wait for the password of the machine to be set
        :param instance: Amazon AMI instance
        :param CancellationContext cancellation_context:
        :return:
        """
        if not instance:
            raise ValueError('Instance cannot be null')

        start_time = time.time()

        password_data = self._get_password(instance)
        while not password_data:
            if time.time() - start_time >= self.timeout:
                raise TimeoutError('Timeout: Waiting for instance to get password')

            self.cancellation_service.check_if_cancelled(cancellation_context)

            time.sleep(self.delay)
            password_data = self._get_password(instance)

        return password_data

    @staticmethod
    def _get_password(instance):
        instance.load()
        password_data = instance.password_data()['PasswordData']
        return password_data

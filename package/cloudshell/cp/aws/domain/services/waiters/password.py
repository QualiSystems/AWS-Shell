import time
from multiprocessing import TimeoutError


class PasswordWaiter(object):
    def __init__(self, delay=5, timeout=15):
        """
        :param delay: the time in seconds between each pull
        :type delay: int
        :param timeout: timeout in minutes until time out exception will raised
        :type timeout: int
        """
        self.delay = delay
        # self.timeout = timeout * 60
        self.timeout = timeout * 2


    def wait(self, instance):
        """
        will wait for the password of the machine to be set
        :param instance: Amazon AMI instance
        :return:
        """
        if not instance:
            raise ValueError('Instance cannot be null')

        start_time = time.time()

        password_data = self._get_password(instance)
        while not password_data:
            if time.time() - start_time >= self.timeout:
                raise TimeoutError('Timeout: Waiting for instance to get password')
            time.sleep(self.delay)
            password_data = self._get_password(instance)

        return password_data

    @staticmethod
    def _get_password(instance):
        instance.load()
        password_data = instance.password_data()['PasswordData']
        return password_data

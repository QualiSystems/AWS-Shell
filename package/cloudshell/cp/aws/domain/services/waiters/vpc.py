import time


class VPCWaiter(object):
    PENDING = 'pending'
    RUNNING = 'available'
    INSTANCE_STATES = [PENDING,
                       RUNNING]

    def __init__(self, delay=2, timeout=10):
        """
        :param delay: the time in seconds between each pull
        :type delay: int
        :param timeout: timeout in minutes until time out exception will raised
        :type timeout: int
        """
        self.delay = delay
        self.timeout = timeout * 60

    def wait(self, vpc, state, load=False):
        """
        Will sync wait for the change of state of the vpc
        :param vpc:
        :param state:
        :param load:
        :return:
        """
        if not vpc:
            raise ValueError('Instance cannot be null')
        if state not in self.INSTANCE_STATES:
            raise ValueError('Unsupported instance state')

        start_time = time.time()
        while vpc.state != state:
            vpc.reload()
            if time.time() - start_time >= self.timeout:
                raise Exception('Timeout: Waiting for instance to be {0} from'.format(state, vpc.state))
            time.sleep(self.delay)

        if load:
            vpc.reload()
        return vpc

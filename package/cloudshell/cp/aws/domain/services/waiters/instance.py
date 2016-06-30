import time


class EC2InstanceWaiter(object):
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

    def __init__(self, delay=2, timeout=10):
        """
        :param delay: the time in seconds between each pull
        :type delay: int
        :param timeout: timeout in minutes until time out exception will raised
        :type timeout: int
        """
        self.delay = delay
        self.timeout = timeout * 60

    def wait(self, instance, state, load=False):
        """
        Will sync wait for the change of state of the instance
        :param instance:
        :param state:
        :param load:
        :return:
        """
        if not instance:
            raise ValueError('Instance cannot be null')
        if state not in self.INSTANCE_STATES:
            raise ValueError('Unsupported instance state')

        start_time = time.time()
        while instance.state['Name'] != state:
            instance.reload()
            if time.time() - start_time >= self.timeout:
                raise Exception('Timeout: Waiting for instance to be {0} from'.format(state, instance.state))
            time.sleep(self.delay)

        if load:
            instance.reload()
        return instance

    def multi_wait(self, instances, state):
        """
        Will sync wait for the change of state of the instance
        :param instances:
        :param state:
        :return:
        """
        if not instances:
            raise ValueError('Instance cannot be null')
        if state not in self.INSTANCE_STATES:
            raise ValueError('Unsupported instance state')

        start_time = time.time()
        last_item = 0
        while len(instances) - last_item:
            instance = instances[last_item]
            if instance.state['Name'] != state:
                instance.reload()
                if time.time() - start_time >= self.timeout:
                    instance = instance or instances[0]
                    raise Exception('Timeout: Waiting for instance to be {0} from'.format(state, instance.state))
                time.sleep(self.delay)
            else:
                last_item += 1

        return instances

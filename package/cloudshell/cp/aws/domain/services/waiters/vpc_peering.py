import time


class VpcPeeringConnectionWaiter(object):
    INITIATING_REQUEST = 'initiating-request',
    PENDING_ACCEPTANCE = 'pending-acceptance'
    ACTIVE = 'active'
    DELETED = 'deleted'
    REJECTED = 'rejected'
    FAILED = 'failed'
    EXPIRED = 'expired'
    PROVISIONING = 'provisioning'
    DELETING = 'deleting'

    STATES = [INITIATING_REQUEST,
              PENDING_ACCEPTANCE,
              ACTIVE,
              DELETED,
              REJECTED,
              FAILED,
              EXPIRED,
              PROVISIONING,
              DELETING]

    def __init__(self, delay=2, timeout=10):
        """
        :param delay: the time in seconds between each pull
        :type delay: int
        :param timeout: timeout in minutes until time out exception will raised
        :type timeout: int
        """
        self.delay = delay
        self.timeout = timeout * 60

    def wait(self, vpc_peering_connection, state, throw_on_error=True, load=False):
        """
        Will sync wait for the change of state of the instance
        :param vpc_peering_connection: vpc_peering_connection object
        :param str state:
        :param boolean throw_on_error: indicates if waiter should throw if in error state
        :param load:
        :return:
        """
        if not vpc_peering_connection:
            raise ValueError('Instance cannot be null')
        if state not in self.STATES:
            raise ValueError('Unsupported vpc peering connection state')

        start_time = time.time()
        while vpc_peering_connection.status['Code'] != state:
            vpc_peering_connection.reload()

            if vpc_peering_connection.status['Code'] == state:
                break
            if throw_on_error and vpc_peering_connection.status['Code'] in [VpcPeeringConnectionWaiter.REJECTED,
                                                                            VpcPeeringConnectionWaiter.FAILED]:
                raise Exception('Error: vpc peering connection state is {0}. Expected state: {1}'
                                .format(vpc_peering_connection.status['Code'], state))

            if time.time() - start_time >= self.timeout:
                raise Exception('Timeout waiting for vpc peering connection to be {0}. Current state is {1}'
                                .format(state, vpc_peering_connection.status['Code']))
            time.sleep(self.delay)

        if load:
            vpc_peering_connection.reload()
        return vpc_peering_connection

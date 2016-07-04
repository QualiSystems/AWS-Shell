from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.waiters.instance import InstanceWaiter


class PowerOperation(object):
    def __init__(self, instance_service, instance_waiter):
        """
        :param InstanceService instance_service:
        :param InstanceWaiter instance_waiter:
        """
        self.instance_service = instance_service
        self.instance_waiter = instance_waiter

    def power_on(self, ec2_session, ami_id):
        """
        will power on the ami
        :param ec2_session: the ec2 connection
        :param ami_id: the ami model
        :type ami_id: str
        :param
        :return:
        """
        instance = self.instance_service.get_instance_by_id(ec2_session, ami_id)
        instance.start()
        self.instance_waiter.wait(instance, self.instance_waiter.RUNNING)
        return True

    def power_off(self, ec2_session, ami_id):
        """
        will power on the ami
        :param ec2_session: the ec2 connection
        :param ami_id: the ami model
        :type ami_id: str
        :param
        :return:
        """
        instance = self.instance_service.get_instance_by_id(ec2_session, ami_id)
        instance.stop()
        self.instance_waiter.wait(instance, self.instance_waiter.STOPPED)
        return True

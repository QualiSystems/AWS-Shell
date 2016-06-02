
class PowerOperation(object):
    def __init__(self, aws_api, instance_waiter):
        """
        :param aws_api: this is the...
        :type aws_api: cloudshell.cp.aws.device_access_layer.aws_api.AWSApi
        :type instance_waiter: cloudshell.cp.aws.domain.services.task_manager.instance_waiter.EC2InstanceWaiter
        """
        self.aws_api = aws_api
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
        instance = self.aws_api.get_instance_by_id(ec2_session, ami_id)
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
        instance = self.aws_api.get_instance_by_id(ec2_session, ami_id)
        instance.stop()
        self.instance_waiter.wait(instance, self.instance_waiter.STOPPED)
        return True

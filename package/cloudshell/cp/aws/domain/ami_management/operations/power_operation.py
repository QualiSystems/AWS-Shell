
class PowerOperation(object):
    def __init__(self, aws_api):
        """
        :param aws_api this is the...
        :type aws_api: cloudshell.cp.aws.device_access_layer.aws_api.AWSApi
        """
        self.aws_api = aws_api

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
        instance.wait_until_running()
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
        instance.wait_until_stopped()
        return True

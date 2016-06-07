

class DeleteAMIOperation(object):
    def __init__(self, aws_ec2_service, instance_waiter, ec2_storage_service, security_group_service):
        """
        :param aws_ec2_service:
        :param EC2InstanceWaiter instance_waiter:
        :param EC2StorageService ec2_storage_service:
        :param AWSSecurityGroupService security_group_service:
        """
        self.aws_ec2_service = aws_ec2_service
        self.instance_waiter = instance_waiter
        self.ec2_storage_service = ec2_storage_service
        self.security_group_service = security_group_service

    def delete_instance(self, ec2_session, instance_id):
        """
        Will terminate the instance
        :param ec2_session: ec2 sessoion
        :param instance_id: the id if the instance
        :type instance_id: str
        :return:
        """
        instance = self.aws_ec2_service.get_instance_by_id(ec2_session, instance_id)

        instance = self._terminate_instance(instance)

        self.security_group_service.delete_all_security_groups_of_instance(instance)
        # self.ec2_storage_service.delete_all_instance_volumes(ec2_session, instance_id)
        return True

    def _terminate_instance(self, instance):
        instance.terminate()
        return self.instance_waiter.wait(instance, self.instance_waiter.TERMINATED)

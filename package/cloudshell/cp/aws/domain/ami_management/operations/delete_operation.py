

class DeleteAMIOperation(object):
    def __init__(self, ec2_api, instance_waiter, ec2_storage_service, security_group_service):
        """
        :param ec2_api:
        :type instance_waiter: cloudshell.cp.aws.domain.services.task_manager.instance_waiter.EC2InstanceWaiter
        :type ec2_storage_service: cloudshell.cp.aws.domain.services.storage_services.ec2_storage_service.EC2StorageService
        :type security_group_service: from cloudshell.cp.aws.domain.services.ec2_services.aws_security_group_service.AWSSecurityGroupService
        """
        self.ec2_api = ec2_api
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
        instance = self.ec2_api.get_instance_by_id(ec2_session, instance_id)

        instance = self._terminate_instance(instance)

        self.security_group_service.delete_all_security_groups_of_instance(instance)
        # self.ec2_storage_service.delete_all_instance_volumes(ec2_session, instance_id)
        return True

    def _terminate_instance(self, instance):
        instance.terminate()
        return self.instance_waiter.wait(instance, self.instance_waiter.TERMINATED)



class DeleteAMIOperation(object):
    def __init__(self, instance_service, ec2_storage_service, security_group_service):
        """
        :param instance_service:
        :param EC2StorageService ec2_storage_service:
        :param SecurityGroupService security_group_service:
        """
        self.instance_service = instance_service
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
        instance = self.instance_service.get_instance_by_id(ec2_session, instance_id)

        instance = self.instance_service.terminate_instance(instance)

        self.security_group_service.delete_all_security_groups_of_instance(instance)
        # self.ec2_storage_service.delete_all_instance_volumes(ec2_session, instance_id)
        return True

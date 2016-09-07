from botocore.exceptions import ClientError

from cloudshell.cp.aws.domain.services.ec2.tags import IsolationTagValues


class DeleteAMIOperation(object):
    def __init__(self, instance_service, ec2_storage_service, security_group_service, tag_service):
        """
        :param instance_service:
        :type instance_service: cloudshell.cp.aws.domain.services.ec2.instance.InstanceService
        :param ec2_storage_service:
        :type ec2_storage_service: cloudshell.cp.aws.domain.services.ec2.ebs.EC2StorageService
        :param security_group_service:
        :type security_group_service: cloudshell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :param tag_service:
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        """
        self.instance_service = instance_service
        self.ec2_storage_service = ec2_storage_service
        self.security_group_service = security_group_service
        self.tag_service = tag_service

    def delete_instance(self, logger, ec2_session, instance_id):
        """
        Will terminate the instance safely
        :param logging.Logger logger:
        :param ec2_session: ec2 sessoion
        :param instance_id: the id if the instance
        :type instance_id: str
        :return:
        """
        try:
            self._delete(ec2_session, instance_id)
        except ClientError as clientErr:
            error = 'Error'
            code = 'Code'
            is_malformed = error in clientErr.response and \
                           code in clientErr.response[error] and \
                           (clientErr.response[error][code] == 'InvalidInstanceID.Malformed' or
                            clientErr.response[error][code] == 'InvalidInstanceID.NotFound')

            if not is_malformed:
                raise
            else:
                logger.info("Aws instance {0} was already terminated".format(instance_id))
                return

    def _delete(self, ec2_session, instance_id):
        """
        Will terminate the instance
        :param ec2_session: ec2 sessoion
        :param instance_id: the id if the instance
        :type instance_id: str
        :return:
        """
        instance = self.instance_service.get_instance_by_id(ec2_session, instance_id)

        # get the security groups before we delete the instance
        try:
            security_groups_description = instance.security_groups
            # in case we have exception the resource is already deleted
        except Exception:
            return True

        vpc_addresses = list(instance.vpc_addresses.all())

        for address in vpc_addresses:
            self.instance_service.release_elastic_address(address)

        self.instance_service.terminate_instance(instance)

        # find the exclusive security groups of the instance and delete them
        if security_groups_description:
            for sg_description in security_groups_description:
                security_group = ec2_session.SecurityGroup(sg_description['GroupId'])
                isolation = self.tag_service.find_isolation_tag_value(security_group.tags)
                if isolation == IsolationTagValues.Exclusive:
                    self.security_group_service.delete_security_group(security_group)

        return True

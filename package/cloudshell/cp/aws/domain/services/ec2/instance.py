from cloudshell.cp.aws.common import retry_helper


class InstanceService(object):
    def __init__(self, tags_creator_service, instance_waiter):
        """
        :param tags_creator_service: Tags Service
        :type tags_creator_service: cloudshell.cp.aws.domain.services.tags.TagService
        :param instance_waiter: Instance Waiter
        :type instance_waiter: cloudshell.cp.aws.domain.services.waiters.instance.InstanceWaiter
        """
        self.instance_waiter = instance_waiter
        self.tags_creator_service = tags_creator_service

    def create_instance(self, ec2_session, name, reservation, ami_deployment_info, ec2_client, wait_for_status_check,
                        cancellation_context, logger):
        """
        Deploys an AMI
        :param wait_for_status_check: bool
        :param ec2_client: boto3.ec2.client
        :param str name: Will assign the deployed vm with the name
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation: reservation model
        :param boto3.ec2.session ec2_session:
        :param cloudshell.cp.aws.models.ami_deployment_model.AMIDeploymentModel ami_deployment_info: request details of the AMI
        :param CancellationContext cancellation_context:
        :param logging.Logger logger: logger
        :return:
        """
        instance = ec2_session.create_instances(
                ImageId=ami_deployment_info.aws_ami_id,
                MinCount=ami_deployment_info.min_count,
                MaxCount=ami_deployment_info.max_count,
                InstanceType=ami_deployment_info.instance_type,
                KeyName=ami_deployment_info.aws_key,
                BlockDeviceMappings=ami_deployment_info.block_device_mappings,
                NetworkInterfaces=ami_deployment_info.network_interfaces,
                IamInstanceProfile=ami_deployment_info.iam_role,
                UserData=ami_deployment_info.user_data
        )[0]

        self.wait_for_instance_to_run_in_aws(ec2_client=ec2_client,
                                             instance=instance,
                                             wait_for_status_check=wait_for_status_check,
                                             cancellation_context=cancellation_context,
                                             logger=logger)

        self._set_tags(instance, name, reservation, ami_deployment_info.custom_tags)

        # Reload the instance attributes
        retry_helper.do_with_retry(lambda: instance.load())
        return instance

    def wait_for_instance_to_run_in_aws(self, ec2_client, instance, wait_for_status_check, cancellation_context,
                                        logger):
        """

        :param ec2_client:
        :param instance:
        :param bool wait_for_status_check:
        :param CancellationContext cancellation_context:
        :param logging.Logger logger:
        :return:
        """
        self.instance_waiter.wait(instance=instance,
                                  state=self.instance_waiter.RUNNING,
                                  cancellation_context=cancellation_context)

        if wait_for_status_check:
            self.instance_waiter.wait_status_ok(ec2_client=ec2_client,
                                                instance=instance,
                                                logger=logger,
                                                cancellation_context=cancellation_context)
            logger.info("Instance created with status: instance_status_ok.")

    def terminate_instance(self, instance):
        return self.terminate_instances([instance])[0]

    def terminate_instances(self, instances):
        if len(instances) == 0:
            return

        for instance in instances:
            instance.terminate()
        return self.instance_waiter.multi_wait(instances, self.instance_waiter.TERMINATED)

    def _set_tags(self, instance, name, reservation, custom_tags):
        # todo create the name with a name generator
        new_name = name + ' ' + instance.instance_id
        default_tags = self.tags_creator_service.get_default_tags(new_name, reservation) + \
                       self.tags_creator_service.get_custom_tags(custom_tags)

        self.tags_creator_service.set_ec2_resource_tags(instance, default_tags)

        for volume in instance.volumes.all():
            self.tags_creator_service.set_ec2_resource_tags(volume, default_tags)

    @staticmethod
    def get_instance_by_id(ec2_session, id):
        return ec2_session.Instance(id=id)

    @staticmethod
    def get_active_instance_by_id(ec2_session, instance_id):
        instance = InstanceService.get_instance_by_id(ec2_session, instance_id)
        if not hasattr(instance, "state") or instance.state['Name'].lower() == 'terminated':
            raise Exception("Can't perform action. EC2 instance was terminated/removed")

        return instance

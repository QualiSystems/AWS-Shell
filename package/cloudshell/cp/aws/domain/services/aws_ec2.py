

class AWSEC2Service(object):
    def __init__(self, tags_creator_service, instance_waiter):
        """
        :param tags_creator_service: Tags Service
        :type tags_creator_service: cloudshell.cp.aws.domain.services.tags.TagService
        :param instance_waiter: Instance Waiter
        :type instance_waiter: cloudshell.cp.aws.domain.services.task_manager.instance_waiter.EC2InstanceWaiter
        """
        self.instance_waiter = instance_waiter
        self.tags_creator_service = tags_creator_service

    def create_instance(self, ec2_session, name, reservation_id, ami_deployment_info):
        """
        Deploys an AMI
        :param name: Will assign the deployed vm with the name
        :type name: str
        :param reservation_id:
        :type reservation_id: str
        :param ec2_session:
        :type ec2_session: boto3.ec2.session
        :param ami_deployment_info: request details of the AMI
        :type ami_deployment_info: cloudshell.cp.aws.models.ami_deployment_model.AMIDeploymentModel
        :return:
        """
        instance = ec2_session.create_instances(
            ImageId=ami_deployment_info.aws_ami_id,
            MinCount=ami_deployment_info.min_count,
            MaxCount=ami_deployment_info.max_count,
            InstanceType=ami_deployment_info.instance_type,
            KeyName=ami_deployment_info.aws_key,
            BlockDeviceMappings=ami_deployment_info.block_device_mappings,
            SecurityGroupIds=ami_deployment_info.security_group_ids,
            NetworkInterfaces=[
                {
                    'SubnetId': ami_deployment_info.subnet_id,
                    'DeviceIndex': 0,
                    'Groups': ami_deployment_info.security_group_ids
                }]
            # PrivateIpAddress=ami_deployment_info.private_ip_address
        )[0]

        self._set_tags(instance, name, reservation_id)

        self.instance_waiter.wait(instance, state=self.instance_waiter.RUNNING)

        # Reload the instance attributes
        instance.load()
        return instance

    def _set_tags(self, instance, name, reservation_id):
        # todo create the name with a name generator
        new_name = name + ' ' + instance.instance_id
        default_tags = self.tags_creator_service.get_default_tags(new_name, reservation_id)
        self.tags_creator_service.set_ec2_resource_tags(instance, default_tags)

    @staticmethod
    def get_instance_by_id(ec2_session, id):
        return ec2_session.Instance(id=id)

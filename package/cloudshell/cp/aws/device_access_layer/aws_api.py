from cloudshell.cp.aws.domain.services.ec2_services.tag_creator_service import TagCreatorService

EC2 = 'ec2'


class AWSApi(object):
    def __init__(self, tags_creator_service):
        """
        :param TagCreatorService tags_creator_service:
        :return:
        """
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
        :type ami_deployment_info: cloudshell.cp.aws.device_access_layer.models.ami_deployment_model.AMIDeploymentModel
        :return:
        """
        instance = ec2_session.create_instances(
            ImageId=ami_deployment_info.aws_ami_id,
            MinCount=ami_deployment_info.min_count,
            MaxCount=ami_deployment_info.max_count,
            InstanceType=ami_deployment_info.instance_type,
            KeyName=ami_deployment_info.aws_key,
            BlockDeviceMappings=ami_deployment_info.block_device_mappings,
            # SecurityGroupIds=ami_deployment_info.security_group_ids,
            NetworkInterfaces=[
                {
                    'SubnetId': ami_deployment_info.subnet_id,
                    'DeviceIndex': 0,
                    'Groups': ami_deployment_info.security_group_ids
                }]
            # PrivateIpAddress=ami_deployment_info.private_ip_address
        )[0]

        # todo create the name with a name generator
        new_name = name + ' ' + instance.instance_id

        default_tags = self.tags_creator_service.get_default_tags(new_name, reservation_id)
        self.set_ec2_resource_tags(instance, default_tags)
        # todo Note: checks every 15 sec, use our waiter instead
        instance.wait_until_running()

        # Reload the instance attributes
        instance.load()
        return instance

    def set_ec2_resource_tags(self, resource, tags):
        resource.create_tags(Tags=tags)

    def get_instance_by_id(self, ec2_session, id):
        return ec2_session.Instance(id=id)

    def create_key_pair(self, ec2_session, key_name):
        return ec2_session.create_key_pair(KeyName=key_name)


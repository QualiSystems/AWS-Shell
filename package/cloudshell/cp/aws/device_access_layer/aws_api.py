from cloudshell.cp.aws.domain.services.ec2_services.tag_manager_service import TagManagerService

EC2 = 'ec2'


class AWSApi(object):
    def __init__(self):
        pass

    @staticmethod
    def create_instance(ec2_session, name, ami_deployment_info):
        """
        Deploys an AMI
        :param name: Will assign the deployed vm with the name
        :type name: str
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
        new_name = name + ' ' + instance.instance_id

        TagManagerService.set_ami_instance_tag(ec2_session, instance, new_name)

        # Note: checks every 15 sec
        instance.wait_until_running()

        # Reload the instance attributes
        instance.load()
        return instance, new_name

    @staticmethod
    def create_security_group(ec2_session, group_name, description, vpc_id):
        return ec2_session.create_security_group(GroupName=group_name,
                                                 Description=description,
                                                 VpcId=vpc_id)

    @staticmethod
    def get_instance_by_id(ec2_session, id):
        return ec2_session.Instance(id=id)

    @staticmethod
    def create_key_pair(ec2_session, key_name):
        return ec2_session.create_key_pair(KeyName=key_name)



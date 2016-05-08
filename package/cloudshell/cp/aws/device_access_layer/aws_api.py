import boto3

EC2 = 'ec2'


class AWSApi(object):
    def __init__(self):
        pass

    def create_ec2_session(self, aws_access_key_id, aws_secret_access_key, region_name):
        session = self._create_session(aws_access_key_id, aws_secret_access_key, region_name)
        return session.resource(EC2)

    def create_instance(self, ec2_session, name, ami_deployment_info):
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
            SecurityGroupIds=ami_deployment_info.security_group_ids,
            # PrivateIpAddress=ami_deployment_info.private_ip_address
        )[0]
        self.set_instance_name(ec2_session, instance, name)

        instance = self.wait_for_instance_running(instance)
        return instance

    @staticmethod
    def _create_session(aws_access_key_id, aws_secret_access_key, region_name):
        return boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name)

    @staticmethod
    def wait_for_instance_running(instance):
        instance.wait_until_running()

        # Reload the instance attributes
        instance.load()
        return instance

    @staticmethod
    def get_instance_by_id(ec2_session, id):
        return ec2_session.Instance(id=id)

    def set_instance_name(self, ec2_session, instance, name):
        return self.set_instance_tag(ec2_session, instance, key='Name', value=name)

    @staticmethod
    def create_key_pair(ec2_session, key_name):
        return ec2_session.create_key_pair(KeyName=key_name)

    @staticmethod
    def set_instance_tag(ec2_session, instance, key, value):
        return ec2_session.create_tags(Resources=[instance.id],
                                       Tags=[{'Key': key, 'Value': value}])

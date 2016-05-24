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
        new_name = name + ' ' + instance.instance_id
        self.set_instance_name_and_createdby(ec2_session, instance, new_name)

        instance = self.wait_for_instance_running(instance)
        return instance, new_name

    @staticmethod
    def _create_session(aws_access_key_id, aws_secret_access_key, region_name):
        if not aws_access_key_id or not aws_secret_access_key:
            return boto3.Session(region_name=region_name)

        return boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name)

    @staticmethod
    def wait_for_instance_running(instance):
        # Note: pulling every 15 sec
        instance.wait_until_running()

        # Reload the instance attributes
        instance.load()
        return instance

    @staticmethod
    def get_instance_by_id(ec2_session, id):
        return ec2_session.Instance(id=id)

    def set_instance_name_and_createdby(self, ec2_session, instance, name):
        return self.set_instance_tag(ec2_session, instance, [self._get_kvp("Name", name),
                                                             self._get_created_by_kvp()])

    @staticmethod
    def create_key_pair(ec2_session, key_name):
        return ec2_session.create_key_pair(KeyName=key_name)

    @staticmethod
    def set_instance_tag(ec2_session, instance, tags):
        return ec2_session.create_tags(Resources=[instance.id], Tags=tags)

    def _get_created_by_kvp(self):
        return self._get_kvp('CreatedBy', 'Quali')

    def _get_kvp(self, key, value):
        return {'Key': key, 'Value': value}

    def create_security_group(self,ec2_session,group_name):
       # ec2_session.create_security_group(GroupName=group_name,)
        pass


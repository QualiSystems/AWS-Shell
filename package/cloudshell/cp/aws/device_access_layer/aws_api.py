import boto3

EC2 = 'ec2'


class AWSApi(object):
    def __init__(self):
        pass

    def create_ec2_session(self, aws_access_key_id, aws_secret_access_key, region_name):
        session = self._create_session(aws_access_key_id, aws_secret_access_key, region_name)
        return session.resource(EC2)

    def _create_session(self, aws_access_key_id, aws_secret_access_key, region_name):
        return boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )

    def create_instance(self,ec2, ami_deployment_info):
        return ec2.create_instances(
            ImageId=ami_deployment_info.image_id,
            MinCount=ami_deployment_info.min_count,
            MaxCount=ami_deployment_info.max_count,
            InstanceType=ami_deployment_info.instance_type,
            KeyName=ami_deployment_info.key_name,
            BlockDeviceMappings=ami_deployment_info.block_device_mappings,
            SecurityGroupIds=ami_deployment_info.security_group_ids,
            PrivateIpAddress=ami_deployment_info.private_ip_address
        )[0]






class AWSApiWrapper(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name):
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.ec2 = self.session.resource('ec2')

    def create_instance(self, ami_deployment_info):
        return self.ec2.create_instances(
            ImageId=ami_deployment_info.image_id,
            MinCount=ami_deployment_info.min_count,
            MaxCount=ami_deployment_info.max_count,
            InstanceType=ami_deployment_info.instance_type,
            KeyName=ami_deployment_info.key_name,
            BlockDeviceMappings=ami_deployment_info.block_device_mappings,
            SecurityGroupIds=ami_deployment_info.security_group_ids,
            PrivateIpAddress=ami_deployment_info.private_ip_address
        )[0]

    def get_instance_by_id(self, id):
        return self.ec2.Instance(id=id)

    def set_instance_name(self, instance, name):
        return self.set_instance_tag(instance, key='Name', value=name)

    def create_key_pair(self, key_name):
        return self.ec2.create_key_pair(KeyName=key_name)

    def set_instance_tag(self, instance, key, value):
        return self.ec2.create_tags(Resources=[instance.id],
                                    Tags=[{'Key': key, 'Value': value}])

    def get_root_device_type(self, instance):
        return instance.root_device_type

    def get_ami_by_id(self, ami_id):
        return self.ec2.images.filter(ImageIds=[ami_id])



















class AMIDeploymentInfoModel():
    def __init__(self):
        self.image_id = 'ami-3acf2f55'
        self.min_count = 1
        self.max_count = 1
        self.instance_type = 't2.nano'
        self.key_name = 'aws_testing_key_pair'
        self.block_device_mappings = [
            {
                # 'VirtualName': 'VNAame',
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    # 'SnapshotId': 'string',
                    'VolumeSize': 30,
                    'DeleteOnTermination': True,
                    'VolumeType': 'gp2',  # 'standard'|'io1'|'gp2'|'sc1'|'st1',
                    # 'Iops': 90,
                    # 'Encrypted': True
                },
                # 'NoDevice': 'string'
            }]
        self.security_group_ids = ['sg-66ea1b0e']
        self.private_ip_address = '172.31.6.6'

class AMIDefaultDeploymentInfoModel(AMIDeploymentInfoModel):
    def __init__(self):
        self.image_id = 'ami-3acf2f55'
        self.min_count = 1
        self.max_count = 1
        self.instance_type = 't2.nano'
        self.key_name = 'aws_testing_key_pair'
        self.block_device_mappings = [
            {
                # 'VirtualName': 'VNAame',
                'DeviceName': '/dev/sda1',
                'Ebs': {
                    # 'SnapshotId': 'string',
                    'VolumeSize': 30,
                    'DeleteOnTermination': True,
                    'VolumeType': 'gp2',  # 'standard'|'io1'|'gp2'|'sc1'|'st1',
                    # 'Iops': 90,
                    # 'Encrypted': True
                },
                # 'NoDevice': 'string'
            }]
        self.security_group_ids = ['sg-66ea1b0e']
        self.private_ip_address = '172.31.6.6'


class AWSLogic:
    def __init__(self):
        self.aws = AWSApiWrapper('AKIAI7K5PJEJ622ZUI4A', 'amT7pYJ/0Sp9KI1SqCuUT+W3ShzPkokW9wgUW7Ho', 'eu-central-1')

    def CreateInstance(self):
        instance = self.aws.create_instance(AMIDefaultDeploymentInfoModel())
        self.aws.set_instance_name(instance, "My Quali instance " + instance.id)
        return instance

# AWSLogic().CreateInstance()

# start working with aws API
# aws = AWSApiWrapper('AKIAI7K5PJEJ622ZUI4A', 'amT7pYJ/0Sp9KI1SqCuUT+W3ShzPkokW9wgUW7Ho', 'eu-central-1')

# ami=aws.get_instance_by_id('ami-3acf2f55')
# print ami

# ins1 = aws.get_instance_by_id('i-c761077b')
# ins2 = aws.get_instance_by_id('i-bdd84001')
# root_device_type = aws.get_root_device_type(ins1)
# print root_device_type

# create instance and set its name
# instance = aws.create_instance(AMIDefaultDeploymentInfoModel())
# aws.set_instance_name(instance, "My Quali instance " + instance.id)
# ins1 = aws.get_instance_by_id(instance.id)
# print ins1

# aws.set_instance_tag(ins1,"TestTAg","someval")

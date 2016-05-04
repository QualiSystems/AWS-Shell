class AMIDeploymentInfoModel(object):
    def __init__(self):
        self.image_id = ''  # type: str
        self.min_count = 0  # type: int
        self.max_count = 0  # type: int
        self.instance_type = ''  # type: str
        self.key_name = ''  # type: str
        self.block_device_mappings = None  # type: list[dict]
        self.security_group_ids = None  # type: list[str]
        self.private_ip_address = ''  # type: str


        # self.image_id = 'ami-3acf2f55'
        # self.min_count = 1
        # self.max_count = 1
        # self.instance_type = 't2.nano'
        # self.key_name = 'aws_testing_key_pair'
        # self.block_device_mappings = [
        #     {
        #         # 'VirtualName': 'VNAame',
        #         'DeviceName': '/dev/sda1',
        #         'Ebs': {
        #             # 'SnapshotId': 'string',
        #             'VolumeSize': 30,
        #             'DeleteOnTermination': True,
        #             'VolumeType': 'gp2',  # 'standard'|'io1'|'gp2'|'sc1'|'st1',
        #             # 'Iops': 90,
        #             # 'Encrypted': True
        #         },
        #         # 'NoDevice': 'string'
        #     }]
        # self.security_group_ids = ['sg-66ea1b0e']
        # self.private_ip_address = '172.31.6.6'

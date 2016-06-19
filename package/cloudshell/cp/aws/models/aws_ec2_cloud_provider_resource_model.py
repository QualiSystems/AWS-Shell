class AWSEc2CloudProviderResourceModel(object):
    def __init__(self):
        self.management_vpc_cidr = ''  # type: str
        self.management_vpc_id = ''  # type: str
        self.management_sg_id = ''  # type: str
        self.key_pairs_location = ''  # type: str
        self.default_instance_type = ''  # type: str
        # storage data
        self.max_storage_size = ''  # type: int
        self.max_storage_iops = ''  # type: int
        self.default_storage_size = ''  # type: int
        self.default_storage_iops = ''  # type: int
        self.device_name = ''  # type: str
        self.delete_on_termination = ''  # type: str   <- deployment option
        # "the volume can be one of these: 'standard'|'io1'|'gp2'|'sc1'|'st1'
        self.region = ''  # type : str
        self.default_storage_type = ''  # type: str
        self.aws_access_key_id = ''  # type: str
        self.aws_secret_access_key = ''  # type: str

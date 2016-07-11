class AWSEc2CloudProviderResourceModel(object):
    def __init__(self):
        self.aws_management_vpc_id = ''  # type: str
        self.aws_management_sg_id = ''  # type: str
        self.key_pairs_location = ''  # type: str
        # storage data
        self.max_storage_size = ''  # type: int
        self.max_storage_iops = ''  # type: int
        self.root_volume_name = ''  # type: str
        self.region = ''  # type : str
        self.aws_access_key_id = ''  # type: str
        self.aws_secret_access_key = ''  # type: str

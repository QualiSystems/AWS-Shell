class AWSEc2CloudProviderResourceModel(object):
    def __init__(self):
        self.management_vpc_cidr = ''  # type: str
        self.management_sg_id = ''  # type: str
        self.keypairs_location = ''  # type: str

        #self.min_count = 0  # type: int
        #self.max_count = 0  # type: int
        self.instance_type = ''  # type: str
        #self.aws_key = ''  # type: str
        #self.security_group_ids = None  # type: str
        #self.private_ip_address = ''  # type: str    <- deployment option
        # storage data
        self.max_storage_size = ''  # type: int
        self.max_storage_iops = ''  # type: int
        self.storage_size = ''  # type: int
        self.storage_iops = ''  # type: int
        self.device_name = ''  # type: str
        self.delete_on_termination = ''  # type: str   <- deployment option
        # "the volume can be one of these: 'standard'|'io1'|'gp2'|'sc1'|'st1'
        self.region = ''  # type : str
        self.storage_type = ''  # type: str

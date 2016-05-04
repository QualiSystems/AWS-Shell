class AWSEc2Datamodel(object):
    def __init__(self):
        self.aws_ami_id = ''  # type: str
        self.storage_size = ''  # type: int
        self.storage_iops = ''  # type: int
        self.management_vpc_cidr = ''  # type: str
        self.management_sg_id = ''  # type: str
        self.aws_key = ''  # type: str
        self.keypairs_location = ''  # type: str
        self.max_storage_size = ''  # type: int
        self.max_storage_iops = ''  # type: int
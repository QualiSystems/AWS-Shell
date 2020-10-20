class AWSEc2CloudProviderResourceModel(object):
    def __init__(self):
        self.aws_management_vpc_id = ''  # type: str
        self.aws_management_sg_id = ''  # type: str
        self.key_pairs_location = ''  # type: str
        self.max_storage_size = ''  # type: int
        self.max_storage_iops = ''  # type: int
        self.region = ''  # type : str
        self.aws_access_key_id = ''  # type: str
        self.aws_secret_access_key = ''  # type: str
        self.instance_type = ''  # type: str
        self.reserved_ips_in_subnet = ''  # type: int
        self.vpc_mode = ''  # type: str
        self.vpc_cidr = ''  # type: str

    @property
    def is_static_vpc_mode(self):
        """
        static vpc mode means that we do not try to assign CIDR from quali server, but always use the same CIDR
        as provided in vpc_cidr attribute.
        the idea is that all sandboxes in associated with this cloud provider, use the same range, same ips, etc
        since they are not peered, and use private ips, this is not an issue.
        :return:
        """
        return self.vpc_mode.lower() == 'static'

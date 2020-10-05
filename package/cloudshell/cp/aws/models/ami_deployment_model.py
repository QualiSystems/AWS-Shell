

class AMIDeploymentModel(object):
    def __init__(self):
        self.aws_ami_id = ''  # type: str
        self.min_count = 0  # type: int
        self.max_count = 0  # type: int
        self.instance_type = ''  # type: str
        self.iam_role = ''  # type: str
        self.private_ip_address = ''  # type: str
        self.security_group_ids = []  # type: list[str]
        self.block_device_mappings = []  # type: list[dict]
        self.network_interfaces = []  # type: list[dict]
        self.aws_key = ''  # type: str
        self.custom_tags = {}  # type: dict
        self.user_data = ''  # type: str

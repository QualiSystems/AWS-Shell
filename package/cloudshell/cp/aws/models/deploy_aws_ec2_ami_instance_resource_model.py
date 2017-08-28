from cloudshell.cp.aws.models.network_actions_models import NetworkAction


class DeployAWSEc2AMIInstanceResourceModel(object):
    def __init__(self):
        self.cloud_provider = ''
        self.aws_ami_id = ''
        self.storage_size = ''
        self.storage_iops = ''
        # the storage type can be one of these: 'standard'|'io1'|'gp2'|'sc1'|'st1'
        self.storage_type = ''  # type: str
        self.min_count = 0  # type: int
        self.max_count = 0  # type: int
        self.instance_type = ''  # type: str
        self.security_group_ids = None  # type: str
        self.private_ip_address = ''  # type: str
        self.root_volume_name = ''  # type: str
        self.delete_on_termination = True  # type: bool
        self.auto_power_off = False  # type: bool
        self.wait_for_ip = False  # type: bool
        self.wait_for_status_check = False  # type: bool
        self.auto_delete = False  # type: bool
        self.autoload = False  # type: bool
        self.outbound_ports = ''  # type: str
        self.inbound_ports = ''  # type: str
        self.wait_for_credentials = ''  # type: str
        self.add_public_ip = False  # type: bool
        self.allocate_elastic_ip = False  # type: bool
        self.user = ''  # type: str
        self.app_name = ''  # type: str
        self.network_configurations = None  # type: list[NetworkAction]

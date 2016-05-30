import uuid

import re

from cloudshell.cp.aws.device_access_layer.models.ami_deployment_model import AMIDeploymentModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult


class DeployAMIOperation(object):
    def __init__(self, aws_api):
        """
        :param aws_api this is the...
        :type aws_api: cloudshell.cp.aws.device_access_layer.aws_api.AWSApi
        """
        self.aws_api = aws_api

    def deploy(self, ec2_session, name, aws_ec2_cp_resource_model, ami_deployment_model):
        """
        :param name: The name of the deployed ami
        :type name: str
        :param ec2_session:
        :param aws_ec2_cp_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_cp_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """

        inbound_ports = self._parse_port_group_attribute(ami_deployment_model.inbound_ports)
        outbound_ports = self._parse_port_group_attribute(ami_deployment_model.outbound_ports)
        security_group_id = None

        # if the deployment model contains inbound / outbound ports
        if inbound_ports or outbound_ports:
            # create a new security port group based on the attributes
            # in the end creates a tag "CreatedBy : Quali"
            security_group = self._create_security_group_with_port_group(ec2_session,
                                                                         inbound_ports,
                                                                         outbound_ports,
                                                                         aws_ec2_cp_resource_model.vpc)
            security_group_id = security_group.group_id

        ami_deployment_info = self._create_deployment_parameters(aws_ec2_cp_resource_model,
                                                                 ami_deployment_model,
                                                                 security_group_id)

        return self.aws_api.create_instance(ec2_session, name, ami_deployment_info)

    def _create_deployment_parameters(self, aws_ec2_resource_model, ami_deployment_model, security_group_id):
        """
        :param aws_ec2_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param security_group_id : The security group of the AMI
        :type security_group_id : str
        """
        aws_model = AMIDeploymentModel()
        if not ami_deployment_model.aws_ami_id:
            raise ValueError('AWS Image Id cannot be empty')

        aws_model.aws_ami_id = ami_deployment_model.aws_ami_id
        aws_model.min_count = 1
        aws_model.max_count = 1
        aws_model.instance_type = ami_deployment_model.instance_type if ami_deployment_model.instance_type else aws_ec2_resource_model.default_instance_type
        aws_model.private_ip_address = ami_deployment_model.private_ip_address if ami_deployment_model.private_ip_address else None
        aws_model.block_device_mappings = self._get_block_device_mappings(ami_deployment_model, aws_ec2_resource_model)
        aws_model.aws_key = ami_deployment_model.aws_key
        aws_model.subnet_id = aws_ec2_resource_model.subnet

        if security_group_id != '' and security_group_id is not None:
            aws_model.security_group_ids.append(security_group_id)
        return aws_model

    @staticmethod
    def _get_block_device_mappings(ami_rm, aws_ec2_rm):
        block_device_mappings = [
            {
                'DeviceName': ami_rm.device_name if ami_rm.device_name else aws_ec2_rm.device_name,
                'Ebs': {
                    'VolumeSize': int(ami_rm.storage_size if ami_rm.storage_size else aws_ec2_rm.default_storage_size),
                    'DeleteOnTermination': ami_rm.delete_on_termination if ami_rm.delete_on_termination else aws_ec2_rm.delete_on_termination,
                    'VolumeType': ami_rm.storage_type if ami_rm.storage_type else aws_ec2_rm.default_storage_type
                }
            }]
        return block_device_mappings

    @staticmethod
    def _parse_port_group_attribute(ports_attribute):

        if ports_attribute:
            splited_ports = ports_attribute.split(';')
            port_data_array = [DeployAMIOperation._single_port_parse(port) for port in splited_ports]
            return port_data_array
        return None

    @staticmethod
    def _single_port_parse(ports_attribute):
        destination = "0.0.0.0/0"
        port_data = None

        from_to_protocol_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+):(?P<protocol>(udp|tcp)))$",ports_attribute)

        # 80-50000:udp
        if from_to_protocol_match:
            from_port = from_to_protocol_match.group('from_port')
            to_port = from_to_protocol_match.group('to_port')
            protocol = from_to_protocol_match.group('protocol')
            return PortData(from_port, to_port, protocol, destination)

        from_protocol_match = re.match(r"^((?P<from_port>\d+):(?P<protocol>(udp|tcp)))$", ports_attribute)

        # 80:udp
        if from_protocol_match:
            from_port = from_protocol_match.group('from_port')
            to_port = from_port
            protocol = from_protocol_match.group('protocol')
            return PortData(from_port, to_port, protocol, destination)

        from_to_match = re.match(r"^((?P<from_port>\d+)-(?P<to_port>\d+))$", ports_attribute)

        # 20-80
        if from_to_match:
            from_port = from_to_match.group('from_port')
            to_port = from_to_match.group('to_port')
            protocol = 'tcp'
            return PortData(from_port, to_port, protocol, destination)

        port_match = re.match(r"^((?P<from_port>\d+))$", ports_attribute)
        # 80
        if port_match:
            from_port = port_match.group('from_port')
            to_port = from_port
            protocol = 'tcp'
            return PortData(from_port, to_port, protocol, destination)

        return port_data

    def _create_security_group_with_port_group(self, ec2_session, inbound_ports, outbound_ports, vpc):

        security_group_name = "Quali_security_group " + str(uuid.uuid4())
        # creating the security group
        description = "Quali Security Group"
        security_group = self.aws_api.create_security_group(ec2_session,
                                                            security_group_name,
                                                            description,
                                                            vpc)
        # adding inbound port rules
        if inbound_ports:
            ip_permissions = [self._get_ip_permission_object(port) for port in inbound_ports if port is not None]
            security_group.authorize_ingress(IpPermissions=ip_permissions)

        if outbound_ports:
            ip_permissions = [self._get_ip_permission_object(port) for port in outbound_ports if port is not None]
            security_group.authorize_egress(IpPermissions=ip_permissions)

        # setting tags on the created security group
        self.aws_api.set_security_group_tags(security_group, security_group_name)

        return security_group

    @staticmethod
    def _get_ip_permission_object(port_data):
        return {
            'IpProtocol': port_data.protocol,
            'FromPort': int(port_data.from_port),
            'ToPort': int(port_data.to_port),
            'IpRanges': [
                {
                    'CidrIp': port_data.destination
                }
            ]}


class PortData(object):
    def __init__(self, from_port, to_port, protocol, destination):
        """ec2_session

        :param port: to_port-start port
        :type port: int
        :param port: from_port-end port
        :type port: int
        :param protocol: protocol-can be UDP or TCP
        :type port: str
        :param destination: Determines the traffic that can leave your instance, and where it can go.
        :type port: str
        :return:
        """
        self.from_port = from_port
        self.to_port = to_port
        self.protocol = protocol
        self.destination = destination

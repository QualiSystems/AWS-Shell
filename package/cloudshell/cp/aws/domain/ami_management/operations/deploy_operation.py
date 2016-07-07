import uuid

from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.tags import IsolationTagValues
from cloudshell.cp.aws.domain.services.parsers.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.ami_deployment_model import AMIDeploymentModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult


class DeployAMIOperation(object):
    def __init__(self, instance_service, ami_credential_service, security_group_service, tag_service,
                 vpc_service, key_pair_service, subnet_service):
        """
        :param instance_service: Instance Service
        :type instance_service: cloudshell.cp.aws.domain.services.ec2.instance.InstanceService
        :param ami_credential_service: AMI Credential Service
        :type ami_credential_service: cloudshell.cp.aws.domain.services.ec2.instance_credentials.InstanceCredentialsService
        :param security_group_service: Security Group Service
        :type security_group_service: cloudshell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :param tag_service: Tag service
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        :param vpc_service: VPC service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc.VPCService
        :param key_pair_service: Key Pair Service
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        :param subnet_service: Subnet Service
        :type subnet_service: cloudshell.cp.aws.domain.services.ec2.subnet.SubnetService
        """

        self.tag_service = tag_service
        self.instance_service = instance_service
        self.security_group_service = security_group_service
        self.credentials_service = ami_credential_service
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service
        self.subnet_serivce = subnet_service

    def deploy(self, ec2_session, s3_session, name, reservation, aws_ec2_cp_resource_model, ami_deployment_model):
        """
        :param ec2_session: EC2 session
        :param s3_session: S3 Session
        :param name: The name of the deployed ami
        :type name: str
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param aws_ec2_cp_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_cp_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """

        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                        reservation_id=reservation.reservation_id)
        if not vpc:
            raise ValueError('VPC is not set for this reservation')

        key_name = self.key_pair_service.get_reservation_key_name(reservation_id=reservation.reservation_id)

        security_group = self._create_security_group_for_instance(ami_deployment_model=ami_deployment_model,
                                                                  ec2_session=ec2_session,
                                                                  reservation=reservation,
                                                                  vpc=vpc)

        ami_deployment_info = self._create_deployment_parameters(aws_ec2_resource_model=aws_ec2_cp_resource_model,
                                                                 ami_deployment_model=ami_deployment_model,
                                                                 vpc=vpc,
                                                                 security_group=security_group,
                                                                 key_pair=key_name,
                                                                 reservation=reservation)

        instance = self.instance_service.create_instance(ec2_session=ec2_session,
                                                         name=name,
                                                         reservation=reservation,
                                                         ami_deployment_info=ami_deployment_info)

        self._set_elastic_ip(ec2_session=ec2_session, instance=instance, ami_deployment_model=ami_deployment_model)

        ami_credentials = self._get_ami_credentials(key_pair_location=aws_ec2_cp_resource_model.key_pairs_location,
                                                    wait_for_credentials=ami_deployment_model.wait_for_credentials,
                                                    instance=instance,
                                                    reservation=reservation,
                                                    s3_session=s3_session)

        deployed_app_attributes = self._prepare_deployed_app_attributes(instance, ami_credentials, ami_deployment_model)

        return DeployResult(vm_name=self._get_name_from_tags(instance),
                            vm_uuid=instance.instance_id,
                            cloud_provider_resource_name=ami_deployment_model.cloud_provider_resource,
                            auto_power_on=ami_deployment_model.auto_power_on,
                            auto_power_off=ami_deployment_model.auto_power_off,
                            wait_for_ip=ami_deployment_model.wait_for_ip,
                            auto_delete=ami_deployment_model.auto_delete,
                            autoload=ami_deployment_model.autoload,
                            inbound_ports=ami_deployment_model.inbound_ports,
                            outbound_ports=ami_deployment_model.outbound_ports,
                            deployed_app_attributes=deployed_app_attributes,
                            deployed_app_address=instance.private_ip_address,
                            public_ip=instance.public_ip_address if ami_deployment_model.add_public_ip else None,
                            elastic_ip=ami_deployment_model.add_elastic_ip)

    def _get_ami_credentials(self, s3_session, key_pair_location, reservation, wait_for_credentials, instance):
        """
        Will load win
        :param s3_session:
        :param key_pair_location:
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param wait_for_credentials:
        :param instance:
        :return:
        :rtype: cloudshell.cp.aws.models.ami_credentials.AMICredentials
        """
        # has value for windows instances only
        if instance.platform:
            key_value = self.key_pair_service.load_key_pair_by_name(s3_session=s3_session,
                                                                    bucket_name=key_pair_location,
                                                                    reservation_id=reservation.reservation_id)

            ami_credentials = self.credentials_service.get_windows_credentials(instance=instance,
                                                                               key_value=key_value,
                                                                               wait_for_password=wait_for_credentials)
            return ami_credentials

        return None

    @staticmethod
    def _get_name_from_tags(result):
        return [tag['Value'] for tag in result.tags if tag['Key'] == 'Name'][0]

    def _create_security_group_for_instance(self,
                                            ami_deployment_model,
                                            ec2_session,
                                            reservation,
                                            vpc):

        if not ami_deployment_model.inbound_ports and not ami_deployment_model.outbound_ports:
            return None

        inbound_ports = PortGroupAttributeParser.parse_port_group_attribute(ami_deployment_model.inbound_ports)
        outbound_ports = PortGroupAttributeParser.parse_port_group_attribute(ami_deployment_model.outbound_ports)
        if not inbound_ports and not outbound_ports:
            return None

        security_group_name = SecurityGroupService.CLOUDSHELL_CUSTOM_SECURITY_GROUP.format(str(uuid.uuid4()))

        security_group = self.security_group_service.create_security_group(ec2_session=ec2_session,
                                                                           vpc_id=vpc.id,
                                                                           security_group_name=security_group_name)

        tags = self.tag_service.get_security_group_tags(name=security_group_name,
                                                        isolation=IsolationTagValues.Exclusive,
                                                        reservation=reservation)

        self.tag_service.set_ec2_resource_tags(security_group, tags)

        self.security_group_service.set_security_group_rules(security_group=security_group,
                                                             inbound_ports=inbound_ports,
                                                             outbound_ports=outbound_ports)

        return security_group

    def _create_deployment_parameters(self,
                                      aws_ec2_resource_model,
                                      ami_deployment_model,
                                      vpc,
                                      security_group,
                                      key_pair,
                                      reservation):
        """
        :param aws_ec2_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param vpc: The reservation VPC
        :param security_group : The security group of the AMI
        :type security_group : securityGroup
        :param key_pair : The Key pair name
        :type key_pair : str
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        """
        aws_model = AMIDeploymentModel()
        if not ami_deployment_model.aws_ami_id:
            raise ValueError('AWS Image Id cannot be empty')

        aws_model.aws_ami_id = ami_deployment_model.aws_ami_id
        aws_model.min_count = 1
        aws_model.max_count = 1
        aws_model.instance_type = ami_deployment_model.instance_type or aws_ec2_resource_model.default_instance_type
        aws_model.private_ip_address = ami_deployment_model.private_ip_address or None
        aws_model.block_device_mappings = self._get_block_device_mappings(ami_deployment_model, aws_ec2_resource_model)
        aws_model.aws_key = key_pair
        aws_model.add_public_ip = ami_deployment_model.add_public_ip

        subnet = self.subnet_serivce.get_subnet_from_vpc(vpc)
        aws_model.subnet_id = subnet.id

        self._set_security_group_param(aws_model, reservation, security_group, vpc)

        return aws_model

    def _set_security_group_param(self, aws_model, reservation, security_group, vpc):
        default_sg_name = self.security_group_service.get_sandbox_security_group_name(reservation.reservation_id)
        default_sg = self.security_group_service.get_security_group_by_name(vpc, default_sg_name)

        aws_model.security_group_ids = [default_sg.id]

        if security_group:
            aws_model.security_group_ids.append(security_group.group_id)

    @staticmethod
    def _get_block_device_mappings(ami_rm, aws_ec2_rm):
        block_device_mappings = [
            {
                'DeviceName': ami_rm.device_name if ami_rm.device_name else aws_ec2_rm.device_name,
                'Ebs': {
                    'VolumeSize': int(ami_rm.storage_size or aws_ec2_rm.default_storage_size),
                    'DeleteOnTermination': True,
                    'VolumeType': ami_rm.storage_type or aws_ec2_rm.default_storage_type
                }
            }]
        return block_device_mappings

    def _set_elastic_ip(self, ec2_session, instance, ami_deployment_model):
        """
        :param ec2_session: EC2 session
        :param instance:
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """
        if ami_deployment_model.add_elastic_ip:
            self.instance_service.associate_elastic_ip(ec2_session=ec2_session,
                                                       instance=instance,
                                                       elastic_ip=ami_deployment_model.add_elastic_ip)

    def _prepare_deployed_app_attributes(self, instance, ami_credentials, ami_deployment_model):
        """

        :param instance:
        :param cloudshell.cp.aws.models.ami_credentials.AMICredentials ami_credentials:
        :param cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :return:
        :rtype: dict
        """
        deployed_app_attr = {}

        if ami_credentials:
            deployed_app_attr['Password'] = ami_credentials.password
            deployed_app_attr['User'] = ami_credentials.user_name

        if ami_deployment_model.add_public_ip:
            deployed_app_attr['Public IP'] = instance.public_ip_address
        if ami_deployment_model.add_elastic_ip:
            deployed_app_attr['Public IP'] = ami_deployment_model.add_elastic_ip

        return deployed_app_attr

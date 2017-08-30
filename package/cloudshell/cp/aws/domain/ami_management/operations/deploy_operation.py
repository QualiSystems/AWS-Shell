import traceback
import uuid
from multiprocessing import TimeoutError

from cloudshell.cp.aws.domain.common.exceptions import CancellationException
from cloudshell.cp.aws.domain.common.list_helper import first_or_default
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.tags import IsolationTagValues
from cloudshell.cp.aws.domain.services.ec2.elastic_ip import ElasticIpService
from cloudshell.cp.aws.domain.services.parsers.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.models.ami_deployment_model import AMIDeploymentModel
from cloudshell.cp.aws.models.deploy_result_model import DeployResult
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.shell.core.driver_context import CancellationContext
from cloudshell.cp.aws.models.network_actions_models import SubnetConnectionParams, DeployNetworkingResultModel, \
    DeployNetworkingResultDto


class DeployAMIOperation(object):
    MAX_IO1_IOPS = 20000

    def __init__(self, instance_service, ami_credential_service, security_group_service, tag_service,
                 vpc_service, key_pair_service, subnet_service, elastic_ip_service, cancellation_service):
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
        :param elastic_ip_service: Elastic Ips Service
        :type elastic_ip_service: ElasticIpService
        :param cancellation_service:
        :type cancellation_service: cloudshell.cp.aws.domain.common.cancellation_service.CommandCancellationService
        """

        self.tag_service = tag_service
        self.instance_service = instance_service
        self.security_group_service = security_group_service
        self.credentials_service = ami_credential_service
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service
        self.subnet_serivce = subnet_service
        self.cancellation_service = cancellation_service
        self.elastic_ip_service = elastic_ip_service

    def deploy(self, ec2_session, s3_session, name, reservation, aws_ec2_cp_resource_model,
               ami_deployment_model, ec2_client, cancellation_context, logger):
        """
        :param ec2_client: boto3.ec2.client
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
        :param logging.Logger logger:
        :param CancellationContext cancellation_context:
        :return: Deploy Result
        :rtype: DeployResult
        """

        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                        reservation_id=reservation.reservation_id)
        if not vpc:
            raise ValueError('VPC is not set for this reservation')

        key_name = self.key_pair_service.get_reservation_key_name(reservation_id=reservation.reservation_id)
        logger.info("Found shared sandbox key pair '{0}'".format(key_name))

        self.cancellation_service.check_if_cancelled(cancellation_context)

        instance = None
        security_group = None
        network_config_results = self._prepare_network_config_results(ami_deployment_model)
        try:
            security_group = self._create_security_group_for_instance(ami_deployment_model=ami_deployment_model,
                                                                      ec2_session=ec2_session,
                                                                      reservation=reservation,
                                                                      vpc=vpc)

            self.cancellation_service.check_if_cancelled(cancellation_context)

            ami_deployment_info = self._create_deployment_parameters(ec2_session=ec2_session,
                                                                     aws_ec2_resource_model=aws_ec2_cp_resource_model,
                                                                     ami_deployment_model=ami_deployment_model,
                                                                     vpc=vpc,
                                                                     security_group=security_group,
                                                                     key_pair=key_name,
                                                                     reservation=reservation,
                                                                     network_config_results=network_config_results)

            instance = self.instance_service.create_instance(ec2_session=ec2_session,
                                                             name=name,
                                                             reservation=reservation,
                                                             ami_deployment_info=ami_deployment_info,
                                                             ec2_client=ec2_client,
                                                             wait_for_status_check=ami_deployment_model.wait_for_status_check,
                                                             cancellation_context=cancellation_context,
                                                             logger=logger)

            self._populate_network_config_results_with_interface_data(instance=instance,
                                                                      network_config_results=network_config_results)

            self.cancellation_service.check_if_cancelled(cancellation_context)

            self.elastic_ip_service.set_elastic_ips(ec2_session=ec2_session,
                                                    ec2_client=ec2_client,
                                                    instance=instance,
                                                    ami_deployment_model=ami_deployment_model,
                                                    network_config_results=network_config_results)

            self.cancellation_service.check_if_cancelled(cancellation_context)

        except Exception as e:
            self._rollback_deploy(ec2_session=ec2_session,
                                  instance_id=self._extract_instance_id_on_cancellation(e, instance),
                                  custom_security_group=security_group,
                                  network_config_results=network_config_results,
                                  logger=logger)
            raise  # re-raise original exception after rollback

        ami_credentials = self._get_ami_credentials(key_pair_location=aws_ec2_cp_resource_model.key_pairs_location,
                                                    wait_for_credentials=ami_deployment_model.wait_for_credentials,
                                                    instance=instance,
                                                    reservation=reservation,
                                                    s3_session=s3_session,
                                                    ami_deployment_model=ami_deployment_model,
                                                    cancellation_context=cancellation_context,
                                                    logger=logger)

        deployed_app_attributes = self._prepare_deployed_app_attributes(instance, ami_credentials, ami_deployment_model)
        network_actions_results_dtos = \
            self._prepare_network_config_results_dto(network_config_results=network_config_results,
                                                     ami_deployment_model=ami_deployment_model)

        return DeployResult(vm_name=self._get_name_from_tags(instance),
                            vm_uuid=instance.instance_id,
                            cloud_provider_resource_name=ami_deployment_model.cloud_provider,
                            auto_power_off=True,
                            wait_for_ip=ami_deployment_model.wait_for_ip,
                            auto_delete=True,
                            autoload=ami_deployment_model.autoload,
                            inbound_ports=ami_deployment_model.inbound_ports,
                            deployed_app_attributes=deployed_app_attributes,
                            deployed_app_address=instance.private_ip_address,
                            public_ip=instance.public_ip_address,
                            network_configuration_results=network_actions_results_dtos)

    def _prepare_network_config_results_dto(self, network_config_results, ami_deployment_model):
        """
        :param list[DeployNetworkingResultModel] network_config_results:
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :return:
         :rtype" list[DeployNetworkingResultDto]
        """
        if not ami_deployment_model.network_configurations:
            return []  # for the moment if we didnt received a connectivity action we shouldnot return anything
        return list(map(self._convertDeployNetworkResultModelToDto, network_config_results))

    def _convertDeployNetworkResultModelToDto(self, network_config_result):
        """
        :param DeployNetworkingResultModel network_config_result:
        :rtype: DeployNetworkingResultDto
        """
        import json
        interface_data_json_str = json.dumps({
            'interface_id': network_config_result.interface_id,
            'device_index': network_config_result.device_index,
            'private_ip': network_config_result.private_ip,
            'public_ip': network_config_result.public_ip,
            'mac_address': network_config_result.mac_address
        })
        return DeployNetworkingResultDto(action_id=network_config_result.action_id,
                                         success=True,
                                         interface_data=interface_data_json_str)

    def _prepare_network_config_results(self, ami_deployment_model):
        """
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :rtype: list[DeployNetworkingResultModel]
        """
        network_config_results = []
        if ami_deployment_model.network_configurations is None:
            network_config_results.append(DeployNetworkingResultModel(''))  # init a result object with empty action id
        else:
            for net_config in ami_deployment_model.network_configurations:
                if isinstance(net_config.connection_params, SubnetConnectionParams):
                    network_config_results.append(DeployNetworkingResultModel(net_config.id))
        return network_config_results

    def _extract_instance_id_on_cancellation(self, exception, instance):
        """
        :param exception:
        :param instance:
        :return:
        """
        instance_id = None
        if exception and hasattr(exception, "data") and exception.data and 'instance_ids' in exception.data:
            instance_id = exception.data['instance_ids'][
                0]  # we assume at this point that we are working on a single app
        elif instance:
            instance_id = instance.id
        return instance_id

    def _get_ami_credentials(self, s3_session, key_pair_location, reservation, wait_for_credentials, instance,
                             ami_deployment_model, cancellation_context, logger):
        """
        Will load win
        :param s3_session:
        :param key_pair_location:
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param wait_for_credentials:
        :param instance:
        :param logging.Logger logger:
        :param CancellationContext cancellation_context:
        :return:
        :rtype: cloudshell.cp.aws.models.ami_credentials.AMICredentials
        """
        # has value for windows instances only
        if instance.platform:
            key_value = self.key_pair_service.load_key_pair_by_name(s3_session=s3_session,
                                                                    bucket_name=key_pair_location,
                                                                    reservation_id=reservation.reservation_id)
            result = None
            try:
                result = self.credentials_service.get_windows_credentials(instance=instance,
                                                                          key_value=key_value,
                                                                          wait_for_password=wait_for_credentials,
                                                                          cancellation_context=cancellation_context)
            except TimeoutError:
                logger.info(
                        "Timeout when waiting for windows credentials. Traceback: {0}".format(traceback.format_exc()))
                return None
        else:
            return None if ami_deployment_model.user else self.credentials_service.get_default_linux_credentials()

        return result

    @staticmethod
    def _get_name_from_tags(result):
        return [tag['Value'] for tag in result.tags if tag['Key'] == 'Name'][0]

    def _create_security_group_for_instance(self, ami_deployment_model, ec2_session, reservation, vpc):
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
        if outbound_ports:
            self.security_group_service.remove_allow_all_outbound_rule(security_group=security_group)

        return security_group

    def _create_deployment_parameters(self, ec2_session, aws_ec2_resource_model, ami_deployment_model, vpc,
                                      security_group, key_pair, reservation, network_config_results):
        """
        :param ec2_session:
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
        :param network_config_results: list of network configuration result objects
        :type network_config_results: list[DeployNetworkingResultModel]
        """
        aws_model = AMIDeploymentModel()
        if not ami_deployment_model.aws_ami_id:
            raise ValueError('AWS Image Id cannot be empty')

        image = ec2_session.Image(ami_deployment_model.aws_ami_id)
        self._validate_image_available(image, ami_deployment_model.aws_ami_id)

        aws_model.aws_ami_id = ami_deployment_model.aws_ami_id
        aws_model.min_count = 1
        aws_model.max_count = 1
        aws_model.instance_type = self._get_instance_item(ami_deployment_model, aws_ec2_resource_model)
        aws_model.private_ip_address = ami_deployment_model.private_ip_address or None
        aws_model.block_device_mappings = self._get_block_device_mappings(image=image,
                                                                          ami_deployment_model=ami_deployment_model,
                                                                          aws_ec2_resource_model=aws_ec2_resource_model)
        aws_model.aws_key = key_pair
        aws_model.add_public_ip = ami_deployment_model.add_public_ip  # todo can we remvoe this?

        subnet = self.subnet_serivce.get_first_subnet_from_vpc(vpc)  # todo can we remvoe this?
        aws_model.subnet_id = subnet.id  # todo can we remvoe this?

        security_group_ids = self._get_security_group_param(reservation, security_group, vpc)
        aws_model.security_group_ids = security_group_ids

        aws_model.network_interfaces = \
            self._prepare_network_interfaces(vpc=vpc,
                                             ami_deployment_model=ami_deployment_model,
                                             security_group_ids=security_group_ids,
                                             network_config_results=network_config_results)

        return aws_model

    def _prepare_network_interfaces(self, vpc, ami_deployment_model, security_group_ids, network_config_results):
        """
        :param vpc: The reservation VPC
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param [str] security_group_ids:
        :param list[DeployNetworkingResultModel] network_config_results: list of network configuration result objects
        :return:
        """
        if ami_deployment_model.network_configurations is None:
            network_config_results[0].device_index = 0
            return [self._get_netwrok_interface_single_subnet(ami_deployment_model, security_group_ids, vpc)]

        if ami_deployment_model.add_public_ip and len(ami_deployment_model.network_configurations) > 1:
            raise ValueError("Public IP option is not supported with multiple subnets")

        net_interfaces = []
        device_index = 0
        exclude_public_ip_prop = len(ami_deployment_model.network_configurations) > 1

        for net_config in ami_deployment_model.network_configurations:
            if not isinstance(net_config.connection_params, SubnetConnectionParams):
                continue
            net_interfaces.append(
                    # todo: add fallback to find subnet by cidr if subnet id doesnt exist
                    self._build_network_interface(subnet_id=net_config.connection_params.subnet_id,
                                                  device_index=device_index,
                                                  groups=security_group_ids,  # todo set groups by subnet id
                                                  public_ip=
                                                  None if exclude_public_ip_prop else ami_deployment_model.add_public_ip))

            # set device index on action result object
            res = first_or_default(network_config_results, lambda x: x.action_id == net_config.id)
            res.device_index = device_index

            device_index += 1

        if len(net_interfaces) == 0:
            network_config_results[0].device_index = 0
            return [self._get_netwrok_interface_single_subnet(ami_deployment_model, security_group_ids, vpc)]

        return net_interfaces

    def _get_netwrok_interface_single_subnet(self, ami_deployment_model, security_group_ids, vpc):
        return self._build_network_interface(
                subnet_id=self.subnet_serivce.get_first_subnet_from_vpc(vpc).subnet_id,
                device_index=0,
                groups=security_group_ids,
                public_ip=ami_deployment_model.add_public_ip)

    def _build_network_interface(self, subnet_id, device_index, groups, public_ip=None):
        net_if = {
            'SubnetId': subnet_id,
            'DeviceIndex': device_index,
            'Groups': groups
        }

        if public_ip is not None:
            net_if['AssociatePublicIpAddress'] = public_ip

        return net_if

    def _get_instance_item(self, ami_deployment_model, aws_ec2_resource_model):
        return ami_deployment_model.instance_type if ami_deployment_model.instance_type else aws_ec2_resource_model.instance_type

    def _get_security_group_param(self, reservation, security_group, vpc):
        default_sg_name = self.security_group_service.get_sandbox_security_group_name(reservation.reservation_id)
        default_sg = self.security_group_service.get_security_group_by_name(vpc, default_sg_name)

        security_group_ids = [default_sg.id]

        if security_group:
            security_group_ids.append(security_group.group_id)

        return security_group_ids

    def _get_block_device_mappings(self, image, ami_deployment_model, aws_ec2_resource_model):
        """
        :param image: A resource representing an EC2 image
        :param aws_ec2_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """

        # find the root device default settings
        root_device = filter(lambda x: x['DeviceName'] == image.root_device_name, image.block_device_mappings)[0]

        # get storage size
        storage_size = int(ami_deployment_model.storage_size)
        if not storage_size:
            storage_size = int(root_device['Ebs']['VolumeSize'])
        if int(aws_ec2_resource_model.max_storage_size) and int(storage_size) > int(
                aws_ec2_resource_model.max_storage_size):
            raise ValueError("Requested storage size is bigger than the max allowed storage size of {0}"
                             .format(aws_ec2_resource_model.max_storage_size))

        # get storage type
        storage_type = ami_deployment_model.storage_type
        if not storage_type or storage_type.lower() == 'auto':
            storage_type = root_device['Ebs']['VolumeType']

        # create mappings obj
        block_device_mappings = [{
            'DeviceName': ami_deployment_model.root_volume_name if ami_deployment_model.root_volume_name else image.root_device_name,
            'Ebs': {
                'VolumeSize': int(storage_size),
                'DeleteOnTermination': True,
                'VolumeType': storage_type,
            }
        }]

        # add iops if needed - storage_iops is required for requests to create io1 volumes only
        if storage_type == 'io1':
            storage_iops = int(ami_deployment_model.storage_iops)

            if not storage_iops:
                if 'Iops' in root_device['Ebs']:
                    storage_iops = int(root_device['Ebs']['Iops'])
                else:
                    storage_iops = self._suggested_iops(storage_size) if \
                        self._suggested_iops(storage_size) < self.MAX_IO1_IOPS else self.MAX_IO1_IOPS

            if int(aws_ec2_resource_model.max_storage_iops) and storage_iops > \
                    int(aws_ec2_resource_model.max_storage_iops):
                raise ValueError("Requested storage IOPS is bigger than the max allowed storage IOPS of {0}"
                                 .format(aws_ec2_resource_model.max_storage_iops))

            block_device_mappings[0]['Ebs']['Iops'] = int(storage_iops)

        return block_device_mappings

    def _suggested_iops(self, storage_size):
        """
        :param int storage_size:
        :return:
        :rtype: int
        """
        return int(storage_size) * 30

    def _set_elastic_ip(self, ec2_session, ec2_client, instance):
        """
        :param ec2_session: EC2 session
        :param ec2_client: EC2 client
        :param instance:
        :return: allocated elastic ip
        :rtype: str
        """
        elastic_ip = self.instance_service.allocate_elastic_address(ec2_client=ec2_client)
        self.instance_service.associate_elastic_ip_to_instance(ec2_session=ec2_session,
                                                               instance=instance,
                                                               elastic_ip=elastic_ip)
        return elastic_ip

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
            if ami_credentials.password:
                deployed_app_attr['Password'] = ami_credentials.password
            deployed_app_attr['User'] = ami_credentials.user_name

        if ami_deployment_model.add_public_ip or ami_deployment_model.allocate_elastic_ip:
            deployed_app_attr['Public IP'] = instance.public_ip_address

        return deployed_app_attr

    def _rollback_deploy(self, ec2_session, instance_id, custom_security_group, network_config_results, logger):
        """

        :param boto3.ec2.client ec2_session:
        :param str instance_id:
        :param custom_security_group: Security Group object
        :param list[DeployNetworkingResultModel] network_config_results:
        :param logging.Logger logger:
        :return:
        """
        logger.info("Starting rollback for deploy operation")

        if instance_id:
            instance = self.instance_service.get_instance_by_id(ec2_session=ec2_session,
                                                                id=instance_id)
            logger.debug("Terminating instance id: {}".format(instance.id))
            self.instance_service.terminate_instance(instance=instance)

        if custom_security_group:
            logger.debug("Deleting custom security group {0} - {1}".format(custom_security_group.id,
                                                                           custom_security_group.group_name))
            self.security_group_service.delete_security_group(custom_security_group)

        if network_config_results and len(network_config_results):
            for r in filter(lambda x: x.public_ip, network_config_results):
                logger.debug("Releasing elastic ip {}".format(r.public_ip))
                self.elastic_ip_service.find_and_release_elastic_address(ec2_session=ec2_session,
                                                                         elastic_ip=r.public_ip)

    def _validate_image_available(self, image, ami_id):
        if hasattr(image, 'state') and image.state == 'available':
            return
        raise ValueError('AMI {} not found'.format(ami_id))

    def _populate_network_config_results_with_interface_data(self, instance, network_config_results):
        """
        :param instance:
        :param list[DeployNetworkingResultModel] network_config_results:
        """
        for interface in instance.network_interfaces_attribute:
            result = first_or_default(network_config_results,
                                      lambda x: x.device_index == interface["Attachment"]["DeviceIndex"])
            result.interface_id = interface["NetworkInterfaceId"]
            result.private_ip = interface["PrivateIpAddress"]
            result.mac_address = interface["MacAddress"]
            if "Association" in interface and "PublicIp" in interface["Association"] \
                    and interface["Association"]["PublicIp"]:
                result.public_ip = interface["Association"]["PublicIp"]

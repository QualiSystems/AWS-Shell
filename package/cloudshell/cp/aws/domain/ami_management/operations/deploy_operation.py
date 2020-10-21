import traceback
import uuid
from multiprocessing import TimeoutError

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.common.list_helper import first_or_default
from cloudshell.cp.aws.domain.common.vm_details_provider import VmDetailsProvider
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.tags import IsolationTagValues, TypeTagValues
from cloudshell.cp.aws.domain.services.ec2.elastic_ip import ElasticIpService
from cloudshell.cp.aws.domain.services.parsers.port_group_attribute_parser import PortGroupAttributeParser
from cloudshell.cp.aws.domain.services.strategy.device_index import *
from cloudshell.cp.aws.models.ami_deployment_model import AMIDeploymentModel
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.shell.core.driver_context import CancellationContext
from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.ec2.instance_credentials import InstanceCredentialsService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.network_interface import NetworkInterfaceService
from cloudshell.cp.aws.models.network_actions_models import DeployNetworkingResultModel
from cloudshell.cp.core.models import ConnectToSubnetActionResult, ConnectToSubnetParams, ConnectSubnet, DeployAppResult
from cloudshell.cp.core.utils import convert_dict_to_attributes_list


class DeployAMIOperation(object):
    MAX_IO1_IOPS = 20000

    def __init__(self, instance_service, ami_credential_service, security_group_service, tag_service,
                 vpc_service, key_pair_service, subnet_service, elastic_ip_service, network_interface_service,
                 cancellation_service, device_index_strategy, vm_details_provider):
        """
        :param InstanceService instance_service: Instance Service
        :param InstanceCredentialsService ami_credential_service: AMI Credential Service
        :param SecurityGroupService security_group_service: Security Group Service
        :param TagService tag_service: Tag service
        :param VPCService vpc_service: VPC service
        :param KeyPairService key_pair_service: Key Pair Service
        :param SubnetService subnet_service: Subnet Service
        :param ElasticIpService elastic_ip_service: Elastic Ips Service
        :param NetworkInterfaceService network_interface_service:
        :param CommandCancellationService cancellation_service:
        :param AbstractDeviceIndexStrategy device_index_strategy:
        :param VmDetailsProvider vm_details_provider:
        """
        self.tag_service = tag_service
        self.instance_service = instance_service
        self.security_group_service = security_group_service
        self.credentials_service = ami_credential_service
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service
        self.subnet_service = subnet_service
        self.cancellation_service = cancellation_service
        self.elastic_ip_service = elastic_ip_service
        self.network_interface_service = network_interface_service
        self.device_index_strategy = device_index_strategy
        self.vm_details_provider = vm_details_provider

    def deploy(self, ec2_session, s3_session, name, reservation, aws_ec2_cp_resource_model,
               ami_deploy_action, network_actions, ec2_client, cancellation_context, logger):
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
        :param ami_deploy_action: The deploy app.
        :type ami_deploy_action: cloudshell.cp.core.models.DeployApp
        :param network_actions: The network actions.
        :type network_actions: cloudshell.cp.core.models.ConnectSubnet
        :param logging.Logger logger:
        :param CancellationContext cancellation_context:
        :return: Deploy Result
        :rtype: list[RequestActionBase]
        """
        ami_deployment_model = ami_deploy_action.actionParams.deployment.customModel
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                        reservation_id=reservation.reservation_id)
        if not vpc:
            raise ValueError('VPC is not set for this reservation')

        key_name = self.key_pair_service.get_reservation_key_name(reservation_id=reservation.reservation_id)
        logger.info("Found shared sandbox key pair '{0}'".format(key_name))

        self.cancellation_service.check_if_cancelled(cancellation_context)

        instance = None
        security_group = None
        network_config_results = self._prepare_network_result_models(network_actions=network_actions)
        try:
            security_group = self._create_security_group_for_instance(ami_deployment_model=ami_deployment_model,
                                                                      ec2_session=ec2_session,
                                                                      reservation=reservation,
                                                                      vpc=vpc,
                                                                      logger=logger)

            self.cancellation_service.check_if_cancelled(cancellation_context)

            ami_deployment_info = self._create_deployment_parameters(ec2_session=ec2_session,
                                                                     aws_ec2_resource_model=aws_ec2_cp_resource_model,
                                                                     ami_deployment_model=ami_deployment_model,
                                                                     network_actions=network_actions,
                                                                     vpc=vpc,
                                                                     security_group=security_group,
                                                                     key_pair=key_name,
                                                                     reservation=reservation,
                                                                     network_config_results=network_config_results,
                                                                     logger=logger)

            instance = self.instance_service.create_instance(
                ec2_session=ec2_session,
                name=name,
                reservation=reservation,
                ami_deployment_info=ami_deployment_info,
                ec2_client=ec2_client,
                wait_for_status_check=ami_deployment_model.wait_for_status_check,
                cancellation_context=cancellation_context,
                logger=logger)

            logger.info("Instance created, populating results with interface data")
            self.instance_service.wait_for_instance_to_run_in_aws(ec2_client=ec2_client,
                                                 instance=instance,
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
                                                    network_actions=network_actions,
                                                    network_config_results=network_config_results,
                                                    logger=logger)

            self.cancellation_service.check_if_cancelled(cancellation_context)

        except Exception as e:
            self._rollback_deploy(ec2_session=ec2_session,
                                  instance_id=self._extract_instance_id_on_cancellation(e, instance),
                                  custom_security_group=security_group,
                                  network_config_results=network_config_results,
                                  logger=logger)
            raise  # re-raise original exception after rollback

        logger.info("Instance {} created, getting ami credentials".format(instance.id))
        ami_credentials = self._get_ami_credentials(key_pair_location=aws_ec2_cp_resource_model.key_pairs_location,
                                                    wait_for_credentials=ami_deployment_model.wait_for_credentials,
                                                    instance=instance,
                                                    reservation=reservation,
                                                    s3_session=s3_session,
                                                    ami_deploy_action=ami_deploy_action,
                                                    cancellation_context=cancellation_context,
                                                    logger=logger)

        logger.info("Preparing result")

        deployed_app_attributes = self._prepare_deployed_app_attributes(ami_credentials=ami_credentials,
                                                                        ami_deployment_model=ami_deployment_model,
                                                                        network_config_results=network_config_results)

        vm_details_data = self.vm_details_provider.create(instance)

        network_actions_results_dtos = \
            self._prepare_network_config_results_dto(network_config_results=network_config_results,
                                                     network_actions=network_actions)

        deploy_app_result = DeployAppResult(vmName=self._get_name_from_tags(instance),
                                            vmUuid=instance.instance_id,
                                            deployedAppAttributes=convert_dict_to_attributes_list(deployed_app_attributes),
                                            deployedAppAddress=instance.private_ip_address,
                                            vmDetailsData=vm_details_data,
                                            deployedAppAdditionalData={'inbound_ports': ami_deployment_model.inbound_ports,
                                                                       'public_ip': instance.public_ip_address})
        deploy_app_result.actionId = ami_deploy_action.actionId
        network_actions_results_dtos.append(deploy_app_result)
        return network_actions_results_dtos

    def _validate_public_subnet_exist_if_requested_public_or_elastic_ips(self, ami_deployment_model, network_actions,
                                                                         logger):
        """
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param cloudshell.cp.core.models.ConnectSubnet network_actions:
        :param logging.Logger logger:
        """

        if ami_deployment_model.add_public_ip or ami_deployment_model.allocate_elastic_ip:
            connect_subnet_actions = filter(lambda x: isinstance(x, ConnectSubnet), network_actions)

            if not any(x.actionParams.isPublic for x in connect_subnet_actions):
                msg = "Cannot deploy app with elastic or public ip when connected only to private subnets"
                logger.error(msg)
                raise ValueError(msg)

    def _prepare_network_config_results_dto(self, network_config_results, network_actions):
        """
        :param list[DeployNetworkingResultModel] network_config_results:
        :param cloudshell.cp.core.models.ConnectSubnet network_actions:
        :return:
         :rtype" list[DeployNetworkingResultDto]
        """
        if not network_actions:
            return []  # for the moment if we didnt received a connectivity action we shouldnot return anything
        return list(map(self._convertDeployNetworkResultModelToDto, network_config_results))

    def _convertDeployNetworkResultModelToDto(self, network_config_result):
        """
        :param DeployNetworkingResultModel network_config_result:
        :rtype: ConnectToSubnetActionResult
        """
        import json
        interface_data_json_str = json.dumps({
            'interface_id': network_config_result.interface_id,
            'IP': network_config_result.private_ip,
            'Public IP': network_config_result.public_ip,
            'Elastic IP': network_config_result.is_elastic_ip,
            'MAC Address': network_config_result.mac_address,
            'Device Index': network_config_result.device_index,
        })
        return ConnectToSubnetActionResult(actionId=network_config_result.action_id,
                                           interface=interface_data_json_str)

    def _prepare_network_result_models(self, network_actions):
        """
        :type cloudshell.cp.core.models.ConnectSubnet network_actions
        :rtype: list[DeployNetworkingResultModel]
        """
        network_config_results = []
        if not network_actions:
            network_config_results.append(DeployNetworkingResultModel(''))  # init a result object with empty action id
        else:
            for net_config in network_actions:
                if isinstance(net_config.actionParams, ConnectToSubnetParams):
                    network_config_results.append(DeployNetworkingResultModel(net_config.actionId))
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
                             ami_deploy_action, cancellation_context, logger):
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
            return None if self._get_deployed_app_resource_user_attribute(ami_deploy_action) else \
                self.credentials_service.get_default_linux_credentials()

        return result

    @staticmethod
    def _get_deployed_app_resource_user_attribute(ami_deploy_action):
        """
        check if deployed app resource has a user attribute, while respecting 2nd gen shell namespaces.
        2nd gen shells are a kind of resource whose attributes are namespaced,
        i.e. User is namespace.User in 2nd gen shells

        :param ami_deploy_action: cloudshell.cp.core.models.DeployApp
        :return:
        """
        attribute_names_in_deployed_resource = ami_deploy_action.actionParams.appResource.attributes.keys()
        return next((attr for attr in attribute_names_in_deployed_resource if attr.split('.')[-1]=='User'))

    @staticmethod
    def _get_name_from_tags(result):
        return [tag['Value'] for tag in result.tags if tag['Key'] == 'Name'][0]

    def _create_security_group_for_instance(self, ami_deployment_model, ec2_session, reservation, vpc, logger):
        if not ami_deployment_model.inbound_ports and not ami_deployment_model.outbound_ports:
            return None

        logger.info("Parsing inbound_ports attribute")

        inbound_ports = PortGroupAttributeParser.parse_port_group_attribute(ami_deployment_model.inbound_ports)
        outbound_ports = PortGroupAttributeParser.parse_port_group_attribute(ami_deployment_model.outbound_ports)
        if not inbound_ports and not outbound_ports:
            logger.info("No data found in inbound_ports attribute")
            return None

        security_group_name = SecurityGroupService.CLOUDSHELL_CUSTOM_SECURITY_GROUP.format(str(uuid.uuid4()))

        security_group = self.security_group_service.create_security_group(ec2_session=ec2_session,
                                                                           vpc_id=vpc.id,
                                                                           security_group_name=security_group_name)

        tags = self.tag_service.get_security_group_tags(name=security_group_name,
                                                        isolation=IsolationTagValues.Exclusive,
                                                        reservation=reservation,
                                                        type=TypeTagValues.InboundPorts)

        self.tag_service.set_ec2_resource_tags(security_group, tags)

        self.security_group_service.set_security_group_rules(security_group=security_group,
                                                             inbound_ports=inbound_ports,
                                                             outbound_ports=outbound_ports)
        if outbound_ports:
            self.security_group_service.remove_allow_all_outbound_rule(security_group=security_group)

        logger.info("Created security group {0} from inbound_ports attribute: {1}"
                    .format(security_group.group_id, ami_deployment_model.inbound_ports))

        return security_group

    def _create_deployment_parameters(self,
                                      ec2_session,
                                      aws_ec2_resource_model,
                                      ami_deployment_model,
                                      network_actions,
                                      vpc,
                                      security_group,
                                      key_pair,
                                      reservation,
                                      network_config_results,
                                      logger):
        """
        :param ec2_session:
        :param aws_ec2_resource_model: The resource model of the AMI deployment option
        :type aws_ec2_resource_model: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param ami_deployment_model: The resource model on which the AMI will be deployed on
        :type ami_deployment_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :param network_actions: The network actions.
        :type network_actions: cloudshell.cp.core.models.ConnectSubnet
        :param vpc: The reservation VPC
        :param security_group : The security group of the AMI
        :type security_group : securityGroup
        :param key_pair : The Key pair name
        :type key_pair : str
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param network_config_results: list of network configuration result objects
        :type network_config_results: list[DeployNetworkingResultModel]
        :param logging.Logger logger:
        """
        aws_model = AMIDeploymentModel()
        if not ami_deployment_model.aws_ami_id:
            raise ValueError('AWS Image Id cannot be empty')

        image = ec2_session.Image(ami_deployment_model.aws_ami_id)
        self._validate_image_available(image, ami_deployment_model.aws_ami_id)

        aws_model.custom_tags = self._get_custom_tags(custom_tags=ami_deployment_model.custom_tags)
        aws_model.user_data = self._get_user_data(user_data_url=ami_deployment_model.user_data_url,
                                                  user_data_run_parameters=ami_deployment_model.user_data_run_parameters)

        aws_model.aws_ami_id = ami_deployment_model.aws_ami_id
        aws_model.iam_role = self._get_iam_instance_profile_request(ami_deployment_model)
        aws_model.min_count = 1
        aws_model.max_count = 1
        aws_model.instance_type = self._get_instance_item(ami_deployment_model, aws_ec2_resource_model)
        aws_model.private_ip_address = ami_deployment_model.private_ip_address or None
        aws_model.block_device_mappings = self._get_block_device_mappings(image=image,
                                                                          ami_deployment_model=ami_deployment_model,
                                                                          aws_ec2_resource_model=aws_ec2_resource_model)
        aws_model.aws_key = key_pair

        security_group_ids = self._get_security_group_param(reservation, security_group, vpc,
                                                            ami_deployment_model.allow_all_sandbox_traffic)
        aws_model.security_group_ids = security_group_ids

        aws_model.network_interfaces = \
            self._prepare_network_interfaces(vpc=vpc,
                                             ami_deployment_model=ami_deployment_model,
                                             network_actions=network_actions,
                                             security_group_ids=security_group_ids,
                                             network_config_results=network_config_results,
                                             logger=logger)

        return aws_model

    def _get_iam_instance_profile_request(self, ami_deployment_model):
        role = ami_deployment_model.iam_role
        if not role:
            return dict()
        if role.startswith('arn:'):
            return {"Arn": role}
        return {"Name": role}

    def _prepare_network_interfaces(self, vpc, ami_deployment_model, network_actions, security_group_ids,
                                    network_config_results,
                                    logger):
        """
        :param vpc: The reservation VPC
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param cloudshell.cp.core.models.ConnectSubnet network_actions:
        :param [str] security_group_ids:
        :param list[DeployNetworkingResultModel] network_config_results: list of network configuration result objects
        :param logging.Logger logger:
        :return:
        """
        if not network_actions:
            logger.info("Single subnet mode detected")
            network_config_results[0].device_index = 0
            return [self.network_interface_service.get_network_interface_for_single_subnet_mode(
                add_public_ip=ami_deployment_model.add_public_ip,
                security_group_ids=security_group_ids,
                vpc=vpc,
                private_ip=ami_deployment_model.private_ip_address)]

        self._validate_network_interfaces_request(ami_deployment_model, network_actions, logger)

        net_interfaces = []
        public_ip_prop_value = \
            None if len(network_actions) > 1 else ami_deployment_model.add_public_ip

        logger.info("Applying device index strategy")
        self.device_index_strategy.apply(network_actions)

        logger.info("Building network interface dtos")
        for net_config in network_actions:
            if not isinstance(net_config.actionParams, ConnectToSubnetParams):
                continue

            device_index = net_config.actionParams.vnicName
            private_ip = self._get_private_ip_for_subnet(ami_deployment_model,
                                                         net_config.actionParams.cidr)

            net_interfaces.append(
                # todo: maybe add fallback to find subnet by cidr if subnet id doesnt exist?
                self.network_interface_service.build_network_interface_dto(
                    subnet_id=net_config.actionParams.subnetId,
                    device_index=device_index,
                    groups=security_group_ids,  # todo: set groups by subnet id
                    public_ip=public_ip_prop_value,
                    private_ip=private_ip))

            # set device index on action result object
            res = first_or_default(network_config_results, lambda x: x.action_id == net_config.actionId)
            res.device_index = device_index

        if len(net_interfaces) == 0:
            logger.info("No network interface dto was created, switching back to single subnet mode")
            network_config_results[0].device_index = 0
            return [self.network_interface_service.get_network_interface_for_single_subnet_mode(
                add_public_ip=ami_deployment_model.add_public_ip,
                security_group_ids=security_group_ids,
                vpc=vpc,
                private_ip=ami_deployment_model.private_ip_address)]

        logger.info("Created dtos for {} network interfaces".format(len(net_interfaces)))

        return net_interfaces

    def _get_private_ip_for_subnet(self, ami_deployment_model, subnet_cidr):
        """
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param str subnet_cidr:
        :return:
        """
        if subnet_cidr and ami_deployment_model.private_ip_addresses_dict and \
                subnet_cidr in ami_deployment_model.private_ip_addresses_dict:
            return ami_deployment_model.private_ip_addresses_dict.get(subnet_cidr)

    def _validate_network_interfaces_request(self, ami_deployment_model, network_actions, logger):
        self._validate_public_ip_with_multiple_subnets(ami_deployment_model, network_actions, logger)
        self._validate_public_subnet_exist_if_requested_public_or_elastic_ips(ami_deployment_model, network_actions,
                                                                              logger)

    def _validate_public_ip_with_multiple_subnets(self, ami_deployment_model, network_actions, logger):
        if ami_deployment_model.add_public_ip and len(network_actions) > 1:
            logger.error("Requested public ip with multiple subnets")
            raise ValueError("Public IP option is not supported with multiple subnets")

    def _get_instance_item(self, ami_deployment_model, aws_ec2_resource_model):
        return ami_deployment_model.instance_type \
            if ami_deployment_model.instance_type \
            else aws_ec2_resource_model.instance_type

    def _get_security_group_param(self, reservation, security_group, vpc, allow_sandbox_traffic):
        security_group_ids = []

        if allow_sandbox_traffic:
            default_sg_name = self.security_group_service.sandbox_default_sg_name(reservation.reservation_id)
        else:
            default_sg_name = self.security_group_service.sandbox_isolated_sg_name(reservation.reservation_id)

        sg = self.security_group_service.get_security_group_by_name(vpc, default_sg_name)
        security_group_ids.append(sg.id)

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

    def _prepare_deployed_app_attributes(self, ami_credentials, ami_deployment_model, network_config_results):
        """

        :param cloudshell.cp.aws.models.ami_credentials.AMICredentials ami_credentials:
        :param cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param list[DeployNetworkingResultModel] network_config_results:
        :return:
        :rtype: dict
        """
        deployed_app_attr = {}

        if ami_credentials:
            if ami_credentials.password:
                deployed_app_attr['Password'] = ami_credentials.password
            deployed_app_attr['User'] = ami_credentials.user_name

        if ami_deployment_model.add_public_ip or ami_deployment_model.allocate_elastic_ip:
            # get the first public ip after sorting the network_config_results by device index
            deployed_app_attr['Public IP'] = \
                first_or_default(sorted(network_config_results, key=lambda x: x.device_index),
                                 lambda x: x.public_ip).public_ip

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

    def _get_custom_tags(self, custom_tags):
        res = {}
        if custom_tags:
            tags_list = custom_tags.split(",")
            res = {r.split(":")[0]: r.split(":")[1] for r in tags_list}
        return res

    def _get_user_data(self, user_data_url, user_data_run_parameters):
        data = "#!/bin/bash\n" + "curl --retry 10 --max-time 5 --retry-max-time 180 {0}  > cs.sh \n".format(
            user_data_url) \
               + "chmod +x cs.sh \n" \
               + "./cs.sh {0}".format(user_data_run_parameters)
        return data

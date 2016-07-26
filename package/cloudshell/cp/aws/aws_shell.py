import botocore
import jsonpickle
from botocore.exceptions import ClientError
from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext

from cloudshell.cp.aws.domain.ami_management.operations.access_key_operation import GetAccessKeyOperation
from cloudshell.cp.aws.domain.ami_management.operations.refresh_ip_operation import RefreshIpOperation
from cloudshell.cp.aws.domain.services.ec2.route_table import RouteTablesService
from cloudshell.cp.aws.domain.services.parsers.command_results_parser import CommandResultsParser
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation
from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupConnectivityOperation
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareConnectivityOperation
from cloudshell.cp.aws.domain.deployed_app.operations.app_ports_operation import DeployedAppPortsOperation
from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.ec2.ebs import EC2StorageService
from cloudshell.cp.aws.domain.services.ec2.instance_credentials import InstanceCredentialsService
from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.parsers.custom_param_extractor import VmCustomParamsExtractor
from cloudshell.cp.aws.domain.services.s3.bucket import S3BucketService
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider
from cloudshell.cp.aws.domain.services.waiters.instance import InstanceWaiter
from cloudshell.cp.aws.domain.services.waiters.password import PasswordWaiter
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc import VPCWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class AWSShell(object):
    def __init__(self):
        self.command_result_parser = CommandResultsParser()
        self.tag_service = TagService()
        self.ec2_instance_waiter = InstanceWaiter()
        self.instance_service = InstanceService(self.tag_service, self.ec2_instance_waiter)
        self.ec2_storage_service = EC2StorageService()
        self.model_parser = AWSModelsParser()
        self.cloudshell_session_helper = CloudshellDriverHelper()
        self.aws_session_manager = AWSSessionProvider()
        self.password_waiter = PasswordWaiter()
        self.vm_custom_params_extractor = VmCustomParamsExtractor()
        self.ami_credentials_service = InstanceCredentialsService(self.password_waiter)
        self.security_group_service = SecurityGroupService()
        self.subnet_waiter = SubnetWaiter()
        self.subnet_service = SubnetService(self.tag_service, self.subnet_waiter)
        self.s3_service = S3BucketService()
        self.vpc_peering_waiter = VpcPeeringConnectionWaiter()
        self.key_pair_service = KeyPairService(self.s3_service)
        self.vpc_waiter = VPCWaiter()
        self.route_tables_service = RouteTablesService()

        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service,
                                      instance_service=self.instance_service,
                                      vpc_waiter=self.vpc_waiter,
                                      vpc_peering_waiter=self.vpc_peering_waiter,
                                      sg_service=self.security_group_service)
        self.prepare_connectivity_operation = \
            PrepareConnectivityOperation(vpc_service=self.vpc_service,
                                         security_group_service=self.security_group_service,
                                         key_pair_service=self.key_pair_service,
                                         tag_service=self.tag_service,
                                         route_table_service=self.route_tables_service)

        self.deploy_ami_operation = DeployAMIOperation(instance_service=self.instance_service,
                                                       ami_credential_service=self.ami_credentials_service,
                                                       security_group_service=self.security_group_service,
                                                       tag_service=self.tag_service,
                                                       vpc_service=self.vpc_service,
                                                       key_pair_service=self.key_pair_service,
                                                       subnet_service=self.subnet_service)

        self.refresh_ip_operation = RefreshIpOperation()

        self.power_management_operation = PowerOperation(instance_service=self.instance_service,
                                                         instance_waiter=self.ec2_instance_waiter)

        self.delete_ami_operation = DeleteAMIOperation(instance_service=self.instance_service,
                                                       ec2_storage_service=self.ec2_storage_service,
                                                       security_group_service=self.security_group_service,
                                                       tag_service=self.tag_service)

        self.clean_up_operation = CleanupConnectivityOperation(vpc_service=self.vpc_service,
                                                               key_pair_service=self.key_pair_service,
                                                               route_table_service=self.route_tables_service)

        self.deployed_app_ports_operation = DeployedAppPortsOperation(self.vm_custom_params_extractor)

        self.access_key_operation = GetAccessKeyOperation(key_pair_service=self.key_pair_service)

    def cleanup_connectivity(self, command_context):
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('Cleanup Connectivity')
                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)

                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)
                    s3_session = self.aws_session_manager.get_s3_session(session, aws_ec2_resource_model)
                    result = self.clean_up_operation.cleanup(ec2_session=ec2_session,
                                                             s3_session=s3_session,
                                                             aws_ec2_data_model=aws_ec2_resource_model,
                                                             reservation_id=command_context.reservation.reservation_id,
                                                             logger=logger)

                    return self.command_result_parser.set_command_result({'driverResponse': {'actionResults': [result]}})

    def prepare_connectivity(self, command_context, request):
        """
        Will create a vpc for the reservation and will peer it with the management vpc
        :param command_context: The Command Context
        :param request: The json request
        :type request: str
        :return:
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('Prepare Connectivity')

                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)

                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)
                    s3_session = self.aws_session_manager.get_s3_session(session, aws_ec2_resource_model)

                    # parse request
                    prepare_connectivity_request = DeployDataHolder(jsonpickle.decode(request))
                    prepare_connectivity_request = getattr(prepare_connectivity_request, 'driverRequest', None)

                    reservation_model = ReservationModel.create_instance_from_reservation(command_context.reservation)

                    if not prepare_connectivity_request:
                        raise ValueError('Invalid prepare connectivity request')

                    results = self.prepare_connectivity_operation.prepare_connectivity(
                        ec2_session=ec2_session,
                        s3_session=s3_session,
                        reservation=reservation_model,
                        aws_ec2_datamodel=aws_ec2_resource_model,
                        request=prepare_connectivity_request,
                        logger=logger)

                    return self.command_result_parser.set_command_result({'driverResponse': {'actionResults': results}})

    def power_on_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('Power On')

                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)

                    resource = command_context.remote_endpoints[0]
                    data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
                    self.power_management_operation.power_on(ec2_session, data_holder.vmdetails.uid)
                    session.SetResourceLiveStatus(resource.fullname, "Online", "Active")

    def power_off_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('Power Off')
                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)

                    resource = command_context.remote_endpoints[0]
                    data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
                    self.power_management_operation.power_off(ec2_session, data_holder.vmdetails.uid)
                    session.SetResourceLiveStatus(resource.fullname, "Offline", "Powered Off")

    def delete_instance(self, command_context):
        """
        Will delete the ami instance
        :param bool delete_resource:
        :param command_context: RemoteCommandContext
        :return:
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('Delete instance')
                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)

                    resource = command_context.remote_endpoints[0]
                    data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                    try:
                        self.delete_ami_operation.delete_instance(ec2_session, data_holder.vmdetails.uid)
                    except ClientError as clientErr:
                        error = 'Error'
                        code = 'Code'
                        malformed = 'InvalidInstanceID.Malformed'

                        is_malformed_ = error in clientErr.response and \
                                        code in clientErr.response[error] and \
                                        clientErr.response[error][code] == malformed

                        if not is_malformed_:
                            raise
                        else:
                            logger.info("Aws instance {0} was already terminated".format(data_holder.vmdetails.uid))
                            return
                    except Exception:
                        raise

    def get_application_ports(self, command_context):
        """
        Will return the application ports in a nicely formated manner
        :param command_context: RemoteCommandContext
        :return:
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                logger.info('Get Application Ports')
                resource = command_context.remote_endpoints[0]
                data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                return self.deployed_app_ports_operation.get_formated_deployed_app_ports(data_holder.vmdetails.vmCustomParams)

    def deploy_ami(self, command_context, deployment_request):
        """
        Will deploy Amazon Image on the cloud provider
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('Deploying AMI')

                    aws_ami_deployment_model, name = self.model_parser.convert_to_deployment_resource_model(deployment_request)
                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)
                    ec2_client = self.aws_session_manager.get_ec2_client(session, aws_ec2_resource_model)
                    s3_session = self.aws_session_manager.get_s3_session(session, aws_ec2_resource_model)

                    reservation_model = ReservationModel.create_instance_from_reservation(command_context.reservation)

                    deploy_data = self.deploy_ami_operation.deploy(ec2_session=ec2_session,
                                                                   s3_session=s3_session,
                                                                   name=name,
                                                                   reservation=reservation_model,
                                                                   aws_ec2_cp_resource_model=aws_ec2_resource_model,
                                                                   ami_deployment_model=aws_ami_deployment_model,
                                                                   ec2_client=ec2_client,
                                                                   logger=logger)

                    return self.command_result_parser.set_command_result(deploy_data)

    def refresh_ip(self, resource_context):
        with LoggingSessionContext(resource_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(resource_context) as session:
                    logger.info('Refresh IP')
                    # Get private ip on deployed resource
                    private_ip_on_resource = AWSModelsParser.get_private_ip_from_connected_resource_details(
                        resource_context)

                    # Get Public IP on deployed resource
                    public_ip_on_resource = AWSModelsParser.get_public_ip_from_connected_resource_details(
                        resource_context)

                    deployed_instance_id = AWSModelsParser.try_get_deployed_connected_resource_instance_id(
                        resource_context)

                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(resource_context.resource)
                    ec2_session = self.aws_session_manager.get_ec2_session(session, aws_ec2_resource_model)

                    resource_fullname = AWSModelsParser.get_connectd_resource_fullname(resource_context)

                    self.refresh_ip_operation.refresh_ip(cloudshell_session=session,
                                                         ec2_session=ec2_session,
                                                         deployed_instance_id=deployed_instance_id,
                                                         private_ip_on_resource=private_ip_on_resource,
                                                         public_ip_on_resource=public_ip_on_resource,
                                                         resource_fullname=resource_fullname)

    def GetAccessKey(self, command_context):
        """
        Returns the pem file for the connected resource
        """
        with LoggingSessionContext(command_context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(command_context) as session:
                    logger.info('GetAccessKey')
                    aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
                    s3_session = self.aws_session_manager.get_s3_session(session, aws_ec2_resource_model)
                    reservation_id = command_context.remote_reservation.reservation_id

                    return self.access_key_operation.get_access_key(s3_session=s3_session,
                                                                    aws_ec2_resource_model=aws_ec2_resource_model,
                                                                    reservation_id=reservation_id)


import jsonpickle

from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from cloudshell.shell.core.context import ResourceCommandContext, ResourceRemoteCommandContext
from cloudshell.cp.aws.domain.common.vm_details_provider import VmDetails
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.domain.ami_management.operations.access_key_operation import GetAccessKeyOperation
from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation
from cloudshell.cp.aws.domain.ami_management.operations.refresh_ip_operation import RefreshIpOperation
from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.common.vm_details_provider import VmDetailsProvider
from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupConnectivityOperation
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareConnectivityOperation
from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContext
from cloudshell.cp.aws.domain.context.client_error import ClientErrorWrapper
from cloudshell.cp.aws.domain.deployed_app.operations.app_ports_operation import DeployedAppPortsOperation
from cloudshell.cp.aws.domain.deployed_app.operations.vm_details_operation import VmDetailsOperation
from cloudshell.cp.aws.domain.services.crypto.cryptography import CryptographyService
from cloudshell.cp.aws.domain.services.ec2.ebs import EC2StorageService
from cloudshell.cp.aws.domain.services.ec2.elastic_ip import ElasticIpService
from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService
from cloudshell.cp.aws.domain.services.ec2.instance_credentials import InstanceCredentialsService
from cloudshell.cp.aws.domain.services.ec2.keypair import KeyPairService
from cloudshell.cp.aws.domain.services.ec2.network_interface import NetworkInterfaceService
from cloudshell.cp.aws.domain.services.ec2.route_table import RouteTablesService
from cloudshell.cp.aws.domain.services.ec2.security_group import SecurityGroupService
from cloudshell.cp.aws.domain.services.ec2.subnet import SubnetService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.domain.services.ec2.vpc import VPCService
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.parsers.command_results_parser import CommandResultsParser
from cloudshell.cp.aws.domain.services.parsers.custom_param_extractor import VmCustomParamsExtractor
from cloudshell.cp.aws.domain.services.parsers.network_actions import NetworkActionsParser
from cloudshell.cp.aws.domain.services.s3.bucket import S3BucketService
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider
from cloudshell.cp.aws.domain.services.strategy.device_index import AllocateMissingValuesDeviceIndexStrategy
from cloudshell.cp.aws.domain.services.waiters.instance import InstanceWaiter
from cloudshell.cp.aws.domain.services.waiters.password import PasswordWaiter
from cloudshell.cp.aws.domain.services.waiters.subnet import SubnetWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc import VPCWaiter
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter
from cloudshell.shell.core.driver_context import CancellationContext

from cloudshell.cp.aws.domain.deployed_app.operations.set_app_security_groups import \
    SetAppSecurityGroupsOperation
from cloudshell.cp.aws.models.network_actions_models import SetAppSecurityGroupActionResult


class AWSShell(object):
    def __init__(self):
        self.command_result_parser = CommandResultsParser()
        self.cancellation_service = CommandCancellationService()
        self.tag_service = TagService()
        self.ec2_instance_waiter = InstanceWaiter(cancellation_service=self.cancellation_service)
        self.instance_service = InstanceService(self.tag_service, self.ec2_instance_waiter)
        self.ec2_storage_service = EC2StorageService()
        self.model_parser = AWSModelsParser()
        self.cloudshell_session_helper = CloudshellDriverHelper()
        self.aws_session_manager = AWSSessionProvider()
        self.password_waiter = PasswordWaiter(self.cancellation_service)
        self.vm_custom_params_extractor = VmCustomParamsExtractor()
        self.ami_credentials_service = InstanceCredentialsService(self.password_waiter)
        self.security_group_service = SecurityGroupService(self.tag_service)
        self.subnet_waiter = SubnetWaiter()
        self.subnet_service = SubnetService(self.tag_service, self.subnet_waiter)
        self.s3_service = S3BucketService()
        self.vpc_peering_waiter = VpcPeeringConnectionWaiter()
        self.key_pair_service = KeyPairService(self.s3_service)
        self.vpc_waiter = VPCWaiter()
        self.route_tables_service = RouteTablesService(self.tag_service)
        self.cryptography_service = CryptographyService()
        self.network_interface_service = NetworkInterfaceService(subnet_service=self.subnet_service)
        self.elastic_ip_service = ElasticIpService()
        self.vm_details_provider = VmDetailsProvider()
        self.client_err_wrapepr = ClientErrorWrapper()

        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service,
                                      instance_service=self.instance_service,
                                      vpc_waiter=self.vpc_waiter,
                                      vpc_peering_waiter=self.vpc_peering_waiter,
                                      sg_service=self.security_group_service,
                                      route_table_service=self.route_tables_service)
        self.prepare_connectivity_operation = \
            PrepareConnectivityOperation(vpc_service=self.vpc_service,
                                         security_group_service=self.security_group_service,
                                         key_pair_service=self.key_pair_service,
                                         tag_service=self.tag_service,
                                         route_table_service=self.route_tables_service,
                                         cryptography_service=self.cryptography_service,
                                         cancellation_service=self.cancellation_service,
                                         subnet_service=self.subnet_service,
                                         subnet_waiter=self.subnet_waiter)

        self.deploy_ami_operation = DeployAMIOperation(instance_service=self.instance_service,
                                                       ami_credential_service=self.ami_credentials_service,
                                                       security_group_service=self.security_group_service,
                                                       tag_service=self.tag_service,
                                                       vpc_service=self.vpc_service,
                                                       key_pair_service=self.key_pair_service,
                                                       subnet_service=self.subnet_service,
                                                       elastic_ip_service=self.elastic_ip_service,
                                                       network_interface_service=self.network_interface_service,
                                                       cancellation_service=self.cancellation_service,
                                                       device_index_strategy=AllocateMissingValuesDeviceIndexStrategy(),
                                                       vm_details_provider=self.vm_details_provider)

        self.refresh_ip_operation = RefreshIpOperation(instance_service=self.instance_service)

        self.power_management_operation = PowerOperation(instance_service=self.instance_service,
                                                         instance_waiter=self.ec2_instance_waiter)

        self.delete_ami_operation = DeleteAMIOperation(instance_service=self.instance_service,
                                                       ec2_storage_service=self.ec2_storage_service,
                                                       security_group_service=self.security_group_service,
                                                       tag_service=self.tag_service,
                                                       elastic_ip_service=self.elastic_ip_service)

        self.clean_up_operation = CleanupConnectivityOperation(vpc_service=self.vpc_service,
                                                               key_pair_service=self.key_pair_service,
                                                               route_table_service=self.route_tables_service)

        self.deployed_app_ports_operation = DeployedAppPortsOperation(self.vm_custom_params_extractor,
                                                                      security_group_service=self.security_group_service,
                                                                      instance_service=self.instance_service)

        self.access_key_operation = GetAccessKeyOperation(key_pair_service=self.key_pair_service)

        self.set_app_security_groups_operation = SetAppSecurityGroupsOperation(instance_service=self.instance_service,
                                                                               tag_service=self.tag_service,
                                                                               security_group_service=self.security_group_service)

        self.vm_details_operation = VmDetailsOperation(instance_service=self.instance_service,
                                                       vm_details_provider=self.vm_details_provider)

    def cleanup_connectivity(self, command_context, request):
        """
        Will delete the reservation vpc and all related resources including all remaining instances
        :param ResourceCommandContext command_context:
        :param request: The json request
        :return: json string response
        :rtype: str
        """

        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Cleanup Connectivity')

                    connectivity_actions = self._request_str_to_actions_list(request)

                    result = self.clean_up_operation \
                        .cleanup(ec2_client=shell_context.aws_api.ec2_client,
                                 ec2_session=shell_context.aws_api.ec2_session,
                                 s3_session=shell_context.aws_api.s3_session,
                                 aws_ec2_data_model=shell_context.aws_ec2_resource_model,
                                 reservation_id=command_context.reservation.reservation_id,
                                 actions=connectivity_actions,
                                 logger=shell_context.logger)
                    return self.command_result_parser.set_command_result(
                        {'driverResponse': {'actionResults': [result]}})

    def prepare_connectivity(self, command_context, request, cancellation_context):
        """
        Will create a vpc for the reservation and will peer it with the management vpc
        :param ResourceCommandContext command_context: The Command Context
        :param request: The json request
        :return: json string response
        :param CancellationContext cancellation_context:
        :rtype: str
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Prepare Connectivity')

                    # parse request
                    connectivity_actions = self._request_str_to_actions_list(request)

                    results = self.prepare_connectivity_operation.prepare_connectivity(
                        ec2_client=shell_context.aws_api.ec2_client,
                        ec2_session=shell_context.aws_api.ec2_session,
                        s3_session=shell_context.aws_api.s3_session,
                        reservation=self.model_parser.convert_to_reservation_model(command_context.reservation),
                        aws_ec2_datamodel=shell_context.aws_ec2_resource_model,
                        actions=connectivity_actions,
                        cancellation_context=cancellation_context,
                        logger=shell_context.logger)

                    return self.command_result_parser.set_command_result({'driverResponse': {'actionResults': results}})

    def _request_str_to_actions_list(self, request):
        decoded_request = jsonpickle.decode(request)
        if not decoded_request.get('driverRequest') or not decoded_request.get('driverRequest').get('actions'):
            raise ValueError('Invalid connectivity request')

        return NetworkActionsParser.parse_network_actions_data(decoded_request['driverRequest']['actions'])

    def power_on_ami(self, command_context):
        """
        Will power on the ami
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Power On')

                    resource = command_context.remote_endpoints[0]
                    data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                    self.power_management_operation.power_on(ec2_session=shell_context.aws_api.ec2_session,
                                                             ami_id=data_holder.vmdetails.uid)

                    shell_context.cloudshell_session.SetResourceLiveStatus(resource.fullname, "Online", "Active")

    def power_off_ami(self, command_context):
        """
        Will power on the ami
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Power Off')

                    resource = command_context.remote_endpoints[0]
                    data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                    self.power_management_operation.power_off(ec2_session=shell_context.aws_api.ec2_session,
                                                              ami_id=data_holder.vmdetails.uid)

                    shell_context.cloudshell_session.SetResourceLiveStatus(resource.fullname, "Offline", "Powered Off")

    def delete_instance(self, command_context):
        """
        Will delete the ami instance
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Delete instance')

                    resource = command_context.remote_endpoints[0]
                    data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                    self.delete_ami_operation.delete_instance(logger=shell_context.logger,
                                                              ec2_session=shell_context.aws_api.ec2_session,
                                                              instance_id=data_holder.vmdetails.uid)

    def get_application_ports(self, command_context):
        """
        Will return the application ports in a nicely formated manner
        :param ResourceRemoteCommandContext command_context:
        :rtype: str
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Get Application Ports')
                    resource = command_context.remote_endpoints[0]

                    # Get instance id
                    deployed_instance_id = self.model_parser.try_get_deployed_connected_resource_instance_id(
                        command_context)

                    # Get Allow all Storage Traffic on deployed resource
                    allow_all_storage_traffic = self.model_parser.get_allow_all_storage_traffic_from_connected_resource_details(command_context)

                    return self.deployed_app_ports_operation.get_app_ports_from_cloud_provider(
                        ec2_session=shell_context.aws_api.ec2_session,
                        instance_id=deployed_instance_id,
                        resource=resource,
                        allow_all_storage_traffic=allow_all_storage_traffic)

    def deploy_ami(self, command_context, deployment_request, cancellation_context):
        """
        Will deploy Amazon Image on the cloud provider
        :param ResourceCommandContext command_context:
        :param JSON Obj deployment_request:
        :param CancellationContext cancellation_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Deploying AMI')

                    aws_ami_deployment_model = self.model_parser.convert_to_deployment_resource_model(deployment_request,
                                                                                                      command_context.resource)

                    deploy_data = self.deploy_ami_operation \
                        .deploy(ec2_session=shell_context.aws_api.ec2_session,
                                s3_session=shell_context.aws_api.s3_session,
                                name=aws_ami_deployment_model.app_name,
                                reservation=self.model_parser.convert_to_reservation_model(command_context.reservation),
                                aws_ec2_cp_resource_model=shell_context.aws_ec2_resource_model,
                                ami_deployment_model=aws_ami_deployment_model,
                                ec2_client=shell_context.aws_api.ec2_client,
                                cancellation_context=cancellation_context,
                                logger=shell_context.logger)

                    return self.command_result_parser.set_command_result(deploy_data)

    def refresh_ip(self, command_context):
        """
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Refresh IP')

                    # Get Private Ip on deployed resource
                    private_ip_on_resource = self.model_parser.get_private_ip_from_connected_resource_details(
                        command_context)
                    # Get Public IP on deployed resource
                    public_ip_on_resource = self.model_parser.get_public_ip_from_connected_resource_details(command_context)
                    # Get instance id
                    deployed_instance_id = self.model_parser.try_get_deployed_connected_resource_instance_id(
                        command_context)
                    # Get connected resource name
                    resource_fullname = self.model_parser.get_connectd_resource_fullname(command_context)

                    self.refresh_ip_operation.refresh_ip(cloudshell_session=shell_context.cloudshell_session,
                                                         ec2_session=shell_context.aws_api.ec2_session,
                                                         deployed_instance_id=deployed_instance_id,
                                                         private_ip_on_resource=private_ip_on_resource,
                                                         public_ip_on_resource=public_ip_on_resource,
                                                         resource_fullname=resource_fullname)

    def get_access_key(self, command_context):
        """
        Returns the pem file for the connected resource
        :param ResourceRemoteCommandContext command_context:
        :rtype str:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('GetAccessKey')
                    reservation_id = self._get_reservation_id(command_context)
                    return self.access_key_operation.get_access_key(s3_session=shell_context.aws_api.s3_session,
                                                                    aws_ec2_resource_model=shell_context.aws_ec2_resource_model,
                                                                    reservation_id=reservation_id)

    def set_app_security_groups(self, context, request):
        """
        Set security groups (inbound rules only)
        :param context: todo - set the type of the parameter
        :param request: The json request
        :return:
        """
        with AwsShellContext(context=context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                with self.client_err_wrapepr.wrap():
                    shell_context.logger.info('Set App Security Groups')

                    reservation = self.model_parser.convert_to_reservation_model(context.reservation)
                    app_security_group_models = self.model_parser.convert_to_app_security_group_models(request)

                    result = self.set_app_security_groups_operation.set_apps_security_groups(
                        app_security_group_models=app_security_group_models,
                        reservation=reservation,
                        ec2_session=shell_context.aws_api.ec2_session,
                        logger=shell_context.logger)

                    json_result = SetAppSecurityGroupActionResult.to_json(result)

                    return json_result

    def get_vm_details(self, context, cancellation_context, requests_json):
        """
        Get vm details for specific deployed app
        :type context: ResourceCommandContext
        :rtype str
        """
        results = []
        vm_details_requests = [VmDetailsRequest(item) for item in
                             DeployDataHolder(jsonpickle.decode(requests_json)).items]

        for request in vm_details_requests:
            if cancellation_context.is_cancelled:
                break

            try:
                with AwsShellContext(context=context, aws_session_manager=self.aws_session_manager) as shell_context:
                    with ErrorHandlingContext(shell_context.logger):
                        with self.client_err_wrapepr.wrap():
                            shell_context.logger.info('Get VmDetails')
                            vm_details = self.vm_details_operation.get_vm_details(request.uuid, shell_context.aws_api.ec2_session)
                            vm_details.app_name = request.app_name
                            results.append(vm_details)
            except Exception as e:
                result = VmDetails()
                result.app_name = request.app_name
                result.error = e.message
                results.append(result)

        return self.command_result_parser.set_command_result(results)

    @staticmethod
    def _get_reservation_id(context):
        reservation_id = None
        reservation = getattr(context, 'reservation', getattr(context, 'remote_reservation', None))
        if reservation:
            reservation_id = reservation.reservation_id
        return reservation_id


class VmDetailsRequest(object):
    def __init__(self, item):
        self.uuid = item.deployedAppJson.vmdetails.uid
        self.app_name = item.deployedAppJson.name
import jsonpickle

from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.common.model_parser import AWSModelParser
from cloudshell.cp.aws.domain.ami_management.operations.access_key_operation import GetAccessKeyOperation
from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation
from cloudshell.cp.aws.domain.ami_management.operations.refresh_ip_operation import RefreshIpOperation
from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from cloudshell.cp.aws.domain.common.vm_details_provider import VmDetailsProvider
from cloudshell.cp.aws.domain.conncetivity.operations.cleanup import CleanupSandboxInfraOperation
from cloudshell.cp.aws.domain.conncetivity.operations.prepare import PrepareSandboxInfraOperation
from cloudshell.cp.aws.domain.conncetivity.operations.route_table import RouteTableOperations
from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContext
from cloudshell.cp.aws.domain.context.client_error import ClientErrorWrapper
from cloudshell.cp.aws.domain.deployed_app.operations.app_ports_operation import DeployedAppPortsOperation
from cloudshell.cp.aws.domain.deployed_app.operations.vm_details_operation import VmDetailsOperation
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
from cloudshell.cp.aws.models.vm_details import VmDetailsRequest
from cloudshell.cp.core.models import RequestActionBase, ActionResultBase, DeployApp, ConnectSubnet
from cloudshell.cp.core.utils import single
from cloudshell.cp.core.models import VmDetailsData


class AWSShell(object):
    def __init__(self):
        self.command_result_parser = CommandResultsParser()
        self.cancellation_service = CommandCancellationService()
        self.client_err_wrapper = ClientErrorWrapper()
        self.tag_service = TagService(client_err_wrapper=self.client_err_wrapper)
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
        self.network_interface_service = NetworkInterfaceService(subnet_service=self.subnet_service)
        self.elastic_ip_service = ElasticIpService()
        self.vm_details_provider = VmDetailsProvider()

        self.vpc_service = VPCService(tag_service=self.tag_service,
                                      subnet_service=self.subnet_service,
                                      instance_service=self.instance_service,
                                      vpc_waiter=self.vpc_waiter,
                                      vpc_peering_waiter=self.vpc_peering_waiter,
                                      sg_service=self.security_group_service,
                                      route_table_service=self.route_tables_service)
        self.prepare_connectivity_operation = \
            PrepareSandboxInfraOperation(vpc_service=self.vpc_service,
                                         security_group_service=self.security_group_service,
                                         key_pair_service=self.key_pair_service,
                                         tag_service=self.tag_service,
                                         route_table_service=self.route_tables_service,
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

        self.clean_up_operation = CleanupSandboxInfraOperation(vpc_service=self.vpc_service,
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

    def cleanup_connectivity(self, command_context, actions):
        """
        Will delete the reservation vpc and all related resources including all remaining instances
        :param ResourceCommandContext command_context:
        :param list[RequestActionBase] actions::
        :return: json string response
        :rtype: str
        """

        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Cleanup Connectivity')

                result = self.clean_up_operation \
                    .cleanup(ec2_client=shell_context.aws_api.ec2_client,
                             ec2_session=shell_context.aws_api.ec2_session,
                             s3_session=shell_context.aws_api.s3_session,
                             aws_ec2_data_model=shell_context.aws_ec2_resource_model,
                             reservation_id=command_context.reservation.reservation_id,
                             actions=actions,
                             logger=shell_context.logger)
                return self.command_result_parser.set_command_result(
                    {'driverResponse': {'actionResults': [result]}})

    def prepare_connectivity(self, command_context, actions, cancellation_context):
        """
        Will create a vpc for the reservation and will peer it with the management vpc
        :param ResourceCommandContext command_context: The Command Context
        :param list[RequestActionBase] actions:
        :return: json string response
        :param CancellationContext cancellation_context:
        :rtype: list[ActionResultBase]
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Prepare Connectivity')

                results = self.prepare_connectivity_operation.prepare_connectivity(
                    ec2_client=shell_context.aws_api.ec2_client,
                    ec2_session=shell_context.aws_api.ec2_session,
                    s3_session=shell_context.aws_api.s3_session,
                    reservation=self.model_parser.convert_to_reservation_model(command_context.reservation),
                    aws_ec2_datamodel=shell_context.aws_ec2_resource_model,
                    actions=actions,
                    cancellation_context=cancellation_context,
                    logger=shell_context.logger)

                return results

    def power_on_ami(self, command_context):
        """
        Will power on the ami
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Power On')

                resource = command_context.remote_endpoints[0]
                data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                self.power_management_operation.power_on(ec2_session=shell_context.aws_api.ec2_session,
                                                         ami_id=data_holder.vmdetails.uid)

    def power_off_ami(self, command_context):
        """
        Will power on the ami
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Power Off')

                resource = command_context.remote_endpoints[0]
                data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

                self.power_management_operation.power_off(ec2_session=shell_context.aws_api.ec2_session,
                                                          ami_id=data_holder.vmdetails.uid)

    def delete_instance(self, command_context):
        """
        Will delete the ami instance
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
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
                shell_context.logger.info('Get Application Ports')
                resource = command_context.remote_endpoints[0]

                # Get instance id
                deployed_instance_id = self.model_parser.try_get_deployed_connected_resource_instance_id(
                    command_context)

                # Get Allow all Storage Traffic on deployed resource
                allow_all_storage_traffic = self.model_parser.get_allow_all_storage_traffic_from_connected_resource_details(
                    command_context)

                return self.deployed_app_ports_operation.get_app_ports_from_cloud_provider(
                    ec2_session=shell_context.aws_api.ec2_session,
                    instance_id=deployed_instance_id,
                    resource=resource,
                    allow_all_storage_traffic=allow_all_storage_traffic)

    def deploy_ami(self, command_context, actions, cancellation_context):
        """
        Will deploy Amazon Image on the cloud provider
        :param ResourceCommandContext command_context:
        :param list[RequestActionBase] actions::
        :param CancellationContext cancellation_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Deploying AMI')

                deploy_action = single(actions, lambda x: isinstance(x, DeployApp))
                network_actions = [a for a in actions if isinstance(a, ConnectSubnet)]

                deploy_data = self.deploy_ami_operation \
                    .deploy(ec2_session=shell_context.aws_api.ec2_session,
                            s3_session=shell_context.aws_api.s3_session,
                            name=deploy_action.actionParams.appName,
                            reservation=self.model_parser.convert_to_reservation_model(command_context.reservation),
                            aws_ec2_cp_resource_model=shell_context.aws_ec2_resource_model,
                            ami_deploy_action=deploy_action,
                            network_actions=network_actions,
                            ec2_client=shell_context.aws_api.ec2_client,
                            cancellation_context=cancellation_context,
                            logger=shell_context.logger)

                return deploy_data

    def refresh_ip(self, command_context):
        """
        :param ResourceRemoteCommandContext command_context:
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Refresh IP')

                # Get Private Ip on deployed resource
                private_ip_on_resource = self.model_parser.get_private_ip_from_connected_resource_details(
                    command_context)
                # Get Public IP on deployed resource
                public_ip_on_resource = self.model_parser.get_public_ip_from_connected_resource_details(
                    command_context)
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
                        shell_context.logger.info('Get VmDetails')
                        vm_details = self.vm_details_operation.get_vm_details(request.uuid,
                                                                              shell_context.aws_api.ec2_session)
                        vm_details.appName = request.app_name
                        results.append(vm_details)
            except Exception as e:
                result = VmDetailsData()
                result.appName = request.app_name
                result.error = e.message
                results.append(result)

        return self.command_result_parser.set_command_result(results)

    def create_route_tables(self, command_context, route_table_request):
        """
        Creates a route table, as well as routes and associates it with whatever subnets are relevant
        Add Peering gateway
        Example route table request:
        {"route_tables": [
            {"name": "myRouteTable1",
            "subnets": ["subnetId1"],
            "routes": [{
                            "name":                 "myRoute1",
                            "address_prefix":       "10.0.1.0/28",
                            "next_hop_type":        "Interface",
                            "next_hop_address":     "10.0.1.15",
            }]},
            {"name": "myRouteTable2",
            "subnets": ["subnetId2", "subnetId3"],
            "routes": [{
                            "name":                 "myRoute2",
                            "address_prefix":       "0.0.0.0/0",
                            "next_hop_type":        "Gateway",
            }]},
            {"name": "myRouteTable3",
            "subnets": ["subnetId4", "subnetId5"],
            "routes": [{
                            "name":                 "myRoute3",
                            "address_prefix":       "0.0.0.0/0",
                            "next_hop_type":        "NatGateway",
                            "next_hop_address":     "10.0.2.15",
            }]}
        ]}

        :param route_table_request:
        :param ResourceCommandContext command_context:
        :param str route_table_request: JSON string
        """
        with AwsShellContext(context=command_context, aws_session_manager=self.aws_session_manager) as shell_context:
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Adding route table')

                route_table_request_models = AWSModelParser.convert_to_route_table_model(route_table_request)
                route_table_operations = RouteTableOperations(logger=shell_context.logger,
                                                     aws_ec2_datamodel=shell_context.aws_ec2_resource_model,
                                                     ec2_session=shell_context.aws_api.ec2_session,
                                                     ec2_client=shell_context.aws_api.ec2_client,
                                                     reservation=self.model_parser.convert_to_reservation_model(
                                                         command_context.reservation),
                                                     vpc_service=self.vpc_service,
                                                     route_table_service=self.route_tables_service,
                                                     subnet_service=self.subnet_service,
                                                     network_interface_service=self.network_interface_service)

                exceptions = []
                try:
                    for route_table_request in route_table_request_models:
                        route_table_operations.operate_create_table_request(route_table_request)
                except Exception as e:
                    shell_context.logger.exception("Error ocurred ")
                    exceptions.append(e)

                if exceptions:
                    raise Exception('CreateRouteTables command finished with errors, see logs for more details')



    @staticmethod
    def _get_reservation_id(context):
        reservation_id = None
        reservation = getattr(context, 'reservation', getattr(context, 'remote_reservation', None))
        if reservation:
            reservation_id = reservation.reservation_id
        return reservation_id

import jsonpickle

from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.device_access_layer.aws_ec2 import AWSEC2Service
from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation
from cloudshell.cp.aws.domain.deployed_app.operations.app_ports_operation import DeployedAppPortsOperation
from cloudshell.cp.aws.domain.services.ec2_services.aws_security_group_service import AWSSecurityGroupService
from cloudshell.cp.aws.domain.services.ec2_services.tag_creator_service import TagCreatorService
from cloudshell.cp.aws.domain.services.model_parser.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider
from cloudshell.cp.aws.domain.services.storage_services.ec2_storage_service import EC2StorageService
from cloudshell.cp.aws.domain.services.task_manager.instance_waiter import EC2InstanceWaiter


class AWSShell(object):
    def __init__(self):
        tag_creator_service = TagCreatorService()
        self.aws_ec2_service = AWSEC2Service(tag_creator_service)
        self.ec2_instance_waiter = EC2InstanceWaiter()
        self.ec2_storage_service = EC2StorageService()
        self.model_parser = AWSModelsParser()
        self.cloudshell_session_helper = CloudshellDriverHelper()
        self.aws_session_manager = AWSSessionProvider()

        self.security_group_service = AWSSecurityGroupService()

        self.deploy_ami_operation = DeployAMIOperation(aws_ec2_service=self.aws_ec2_service,
                                                       security_group_service=self.security_group_service,
                                                       tag_creator_service=tag_creator_service)

        self.power_management_operation = PowerOperation(aws_ec2_service=self.aws_ec2_service,
                                                         instance_waiter=self.ec2_instance_waiter)

        self.delete_ami_operation = DeleteAMIOperation(aws_ec2_service=self.aws_ec2_service,
                                                       instance_waiter=self.ec2_instance_waiter,
                                                       ec2_storage_service=self.ec2_storage_service,
                                                       security_group_service=self.security_group_service)

        self.deployed_app_ports_operation = DeployedAppPortsOperation()

    def deploy_ami(self, command_context, deployment_request):
        """
        Will deploy Amazon Image on the cloud provider
        """
        aws_ami_deployment_model, name = self.model_parser.convert_to_deployment_resource_model(deployment_request)
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)
        reservation_id = command_context.reservation.reservation_id

        deploy_data = self.deploy_ami_operation.deploy(ec2_session=ec2_session,
                                                       name=name,
                                                       reservation_id=reservation_id,
                                                       aws_ec2_cp_resource_model=aws_ec2_resource_model,
                                                       ami_deployment_model=aws_ami_deployment_model)

        return self._set_command_result(deploy_data)

    def power_on_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.remote_reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)

        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
        result = self.power_management_operation.power_on(ec2_session, data_holder.vmdetails.uid)
        cloudshell_session.SetResourceLiveStatus(resource.fullname, "Online", "Active")
        return self._set_command_result(result)

    def power_off_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.remote_reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)

        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
        result = self.power_management_operation.power_off(ec2_session, data_holder.vmdetails.uid)
        cloudshell_session.SetResourceLiveStatus(resource.fullname, "Offline", "Powered Off")
        return self._set_command_result(result)

    def delete_ami(self, command_context, delete_resource=True):
        """
        Will delete the ami instance
        :param bool delete_resource:
        :param command_context: RemoteCommandContext
        :return:
        """
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.remote_reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)

        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
        result = self.delete_ami_operation.delete_instance(ec2_session, data_holder.vmdetails.uid)

        # todo this is temporary for the demo
        if delete_resource:
            cloudshell_session.DeleteResource(resourceFullPath=resource.fullname)

        return self._set_command_result(result)

    def get_application_ports(self, command_context):
        """
        Will return the application ports in a nicely formated manner
        :param command_context: RemoteCommandContext
        :return:
        """
        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)

        return self.deployed_app_ports_operation.get_formated_deployed_app_ports(data_holder.vmdetails.vmCustomParams)


    @staticmethod
    def _set_command_result(result, unpicklable=False):
        """
        Serializes output as JSON and writes it to console output wrapped with special prefix and suffix
        :param result: Result to return
        :param unpicklable: If True adds JSON can be deserialized as real object.
                            When False will be deserialized as dictionary
        """
        json = jsonpickle.encode(result, unpicklable=unpicklable)
        result_for_output = str(json)
        return result_for_output

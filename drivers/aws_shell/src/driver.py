from cloudshell.shell.core.driver_context import AutoLoadDetails
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.core import DriverRequestParser
from cloudshell.cp.core.models import DeployApp, DriverResponse
from cloudshell.cp.core.utils import single
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.core.models import ConnectSubnet


class AWSShellDriver(ResourceDriverInterface):
    def cleanup(self):
        pass

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        self.aws_shell = AWSShell()
        self.request_parser = DriverRequestParser()
        self.request_parser.add_deployment_model(deployment_model_cls=DeployAWSEc2AMIInstanceResourceModel)
        self.deployments = dict()
        self.deployments['AWS EC2 Instance'] = self.deploy_ami

    def initialize(self, context):
        pass

    def Deploy(self, context, request=None, cancellation_context=None):
        actions = self.request_parser.convert_driver_request_to_actions(request)
        deploy_action = single(actions, lambda x: isinstance(x, DeployApp))
        deployment_name = deploy_action.actionParams.deployment.deploymentPath
        self.parse_vnicename(actions)

        if deployment_name in self.deployments.keys():
            deploy_method = self.deployments[deployment_name]
            deploy_result = deploy_method(context, actions, cancellation_context)
            return DriverResponse(deploy_result).to_driver_response_json()
        else:
            raise Exception('Could not find the deployment')

    def parse_vnicename(self, actions):
        network_actions = [a for a in actions if isinstance(a, ConnectSubnet)]
        for network_action in network_actions:
            try:
                network_action.actionParams.vnicName = int(network_action.actionParams.vnicName)
            except:
                network_action.actionParams.vnicName = None

    def deploy_ami(self, context, actions, cancellation_context):
        return self.aws_shell.deploy_ami(context, actions, cancellation_context)

    def PowerOn(self, context, ports):
        return self.aws_shell.power_on_ami(context)

    def PowerOff(self, context, ports):
        return self.aws_shell.power_off_ami(context)

    def PowerCycle(self, context, ports, delay):
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        return self.aws_shell.refresh_ip(context)

    def DeleteInstance(self, context, ports):
        return self.aws_shell.delete_instance(context)

    def PrepareSandboxInfra(self, context, request, cancellation_context):
        actions = self.request_parser.convert_driver_request_to_actions(request)
        action_results = self.aws_shell.prepare_connectivity(context, actions, cancellation_context)
        return DriverResponse(action_results).to_driver_response_json()

    def CleanupSandboxInfra(self, context, request):
        actions = self.request_parser.convert_driver_request_to_actions(request)
        return self.aws_shell.cleanup_connectivity(context, actions)

    def GetApplicationPorts(self, context, ports):
        return self.aws_shell.get_application_ports(context)

    def get_inventory(self, context):
        return AutoLoadDetails([], [])

    def GetAccessKey(self, context, ports):
        return self.aws_shell.get_access_key(context)

    def SetAppSecurityGroups(self, context, request):
        return self.aws_shell.set_app_security_groups(context, request)

    def GetVmDetails(self, context, cancellation_context, requests):
        return self.aws_shell.get_vm_details(context, cancellation_context, requests)

    def AddCustomTags(self, context, request, ports):
        return self.aws_shell.add_custom_tags(context, request)

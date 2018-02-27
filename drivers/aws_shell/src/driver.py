import jsonpickle
from cloudshell.shell.core.driver_context import AutoLoadDetails
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.cp.aws.aws_shell import AWSShell


class AWSShellDriver(ResourceDriverInterface):
    def cleanup(self):
        pass

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        self.aws_shell = AWSShell()
        self.deployments = dict()
        self.deployments['AWS EC2 Instance'] = self.deploy_ami

    def initialize(self, context):
        pass

    def Deploy(self, context, request=None, cancellation_context=None):
        app_request = jsonpickle.decode(request)
        deployment_name = app_request['DeploymentServiceName']
        if deployment_name in self.deployments.keys():
            deploy_method = self.deployments[deployment_name]
            return deploy_method(context, request, cancellation_context)
        else:
            raise Exception('Could not find the deployment')

    def deploy_ami(self, context, request, cancellation_context):
        return self.aws_shell.deploy_ami(context, request, cancellation_context)

    def PowerOn(self, context, ports):
        return self.aws_shell.power_on_ami(context)

    def PowerOff(self, context, ports):
        return self.aws_shell.power_off_ami(context)

    def PowerCycle(self, context, ports, delay):
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        return self.aws_shell.refresh_ip(context)

    def destroy_vm_only(self, context, ports):
        return self.aws_shell.delete_instance(context)

    def PrepareConnectivity(self, context, request, cancellation_context):
        return self.aws_shell.prepare_connectivity(context, request, cancellation_context)

    def CleanupConnectivity(self, context, request):
        return self.aws_shell.cleanup_connectivity(context, request)

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
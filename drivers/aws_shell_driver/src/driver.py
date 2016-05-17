from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.cp.aws.aws_shell import AWSShell
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel


class AWSShellDriver(ResourceDriverInterface):
    def cleanup(self):
        pass

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        self.aws_shell = AWSShell()
        pass

    def initialize(self, context):
        pass

    def deploy_ami(self, context, request):
        return self.aws_shell.deploy_ami(context,request)

    def PowerOn(self, context, ports):
        pass

    def PowerOff(self, context, ports):
        pass

    def PowerCycle(self, context, ports, delay):
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        pass

    def delete(self, context, ports):
        pass

    def ApplyConnectivityChanges(self, context, ports, request):
        pass

    def PrepareConnectivityChanges(self, context, request):
        pass

    def get_inventory(self, context):
        pass

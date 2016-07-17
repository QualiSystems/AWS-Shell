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
        pass

    def initialize(self, context):
        pass

    def deploy_ami(self, context, request):
        return self.aws_shell.deploy_ami(context, request)

    def PowerOn(self, context, ports):
        return self.aws_shell.power_on_ami(context)

    def PowerOff(self, context, ports):
        return self.aws_shell.power_off_ami(context)

    def PowerCycle(self, context, ports, delay):
        pass

    def remote_refresh_ip(self, context, ports, cancellation_context):
        return self.aws_shell.refresh_ip(context)


    def destroy_vm_only(self, context, ports):
        return self.aws_shell.delete_ami(context)

    def ApplyConnectivityChanges(self, context, request):
        raise DeprecationWarning('AWS EC2 Apps don\'t support this type of connectivity. '
                                 'All AWS EC2 Apps in the same Sandbox are on the same isolated subnet '
                                 'and can interact with each other')

    def PrepareConnectivity(self, context, request):
        return self.aws_shell.prepare_connectivity(context, request)

    def CleanupConnectivity(self, context, request):
        return self.aws_shell.cleanup_connectivity(context)

    def GetApplicationPorts(self, context, ports):
        return self.aws_shell.get_application_ports(context)

    def get_inventory(self, context):
        return AutoLoadDetails([], [])

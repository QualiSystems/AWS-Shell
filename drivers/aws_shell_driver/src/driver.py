from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface


class AWSShellDriver(ResourceDriverInterface):
    def cleanup(self):
        pass

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        pass

    def deploy_ami(self, context, ports, request):
        pass

    def PowerOn(self, context, ports):
        pass

    def PowerOff(self, context, ports):
        pass

    def PowerCycle(self, context, ports, delay):
        pass

    def refresh_ip(self, context, ports, cancellation_context):
        pass

    def delete(self, context, ports):
        pass

    def ApplyConnectivityChanges(self, context, ports, request):
        pass

    def PrepareConnectivityChanges(self, context, request):
        pass

    def get_inventory(self, context):
        pass

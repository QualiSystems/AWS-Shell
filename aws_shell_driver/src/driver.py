from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface


class {{cookiecutter.project_camel_name}}Driver (ResourceDriverInterface):

    def cleanup(self):
        pass

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
       pass

    def initialize(self, context):
        pass

    def method_one(self, context, request):
		pass


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

    def GetVmDetails(self, context, ports):
        return self.aws_shell.get_vm_details(context)

    def remote_set_aim_role(self, context, iam_instance_profile_arn, ports):
        """
        :param cloudshell.shell.core.context.ResourceCommandContext context:
        :param str iam_instance_profile_arn:
        :param ports:
        :return:
        """
        from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContext
        with AwsShellContext(context=context, aws_session_manager=self.aws_shell.aws_session_manager) as shell_context:
            from cloudshell.core.context.error_handling_context import ErrorHandlingContext
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Set AIM Role')

                # Get instance id
                deployed_instance_id = \
                    self.aws_shell.model_parser.try_get_deployed_connected_resource_instance_id(context)

                # Get IAM Instance profile associations
                result = shell_context.aws_api.ec2_client.describe_iam_instance_profile_associations(
                        Filters=[{'Name': 'instance-id', 'Values': [deployed_instance_id]},
                                 {'Name': 'state', 'Values': ['associating', 'associated']}]
                )

                # Check if current associations contain the requested ARN
                if self._instance_profile_associations_exists(result):
                    from cloudshell.cp.aws.domain.common.list_helper import first_or_default
                    association = first_or_default(result['IamInstanceProfileAssociations'],
                                                   lambda x: x['IamInstanceProfile']['Arn'] == iam_instance_profile_arn)
                    if not association:
                        # Remove current IAM associations
                        for ass in result['IamInstanceProfileAssociations']:
                            shell_context.aws_api.ec2_client.disassociate_iam_instance_profile(
                                    AssociationId=ass['AssociationId'])
                    else:
                        shell_context.logger.info('Requested IAM ARN {0} already associated with instance'
                                                  .format(iam_instance_profile_arn))
                        return

                # Associate IAM ARN with instance
                shell_context.aws_api.ec2_client.associate_iam_instance_profile(
                        InstanceId=deployed_instance_id,
                        IamInstanceProfile={
                            'Arn': iam_instance_profile_arn
                        }
                )

    def remote_attach_volume(self, context, device, volume_id, ports):
        from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContext
        with AwsShellContext(context=context, aws_session_manager=self.aws_shell.aws_session_manager) as shell_context:
            from cloudshell.core.context.error_handling_context import ErrorHandlingContext
            with ErrorHandlingContext(shell_context.logger):
                shell_context.logger.info('Attach volume {1} to device {0}'.format(device, volume_id))

                # Get instance id
                deployed_instance_id = \
                    self.aws_shell.model_parser.try_get_deployed_connected_resource_instance_id(context)

                # Get instance object
                instance = shell_context.aws_api.ec2_session.Instance(deployed_instance_id)

                # Attach volume
                instance.attach_volume(Device=device, VolumeId=volume_id)

    def remote_detach_volume(self, context, device, volume_id, force, ports):
        from cloudshell.cp.aws.domain.context.aws_shell import AwsShellContext
        with AwsShellContext(context=context, aws_session_manager=self.aws_shell.aws_session_manager) as shell_context:
            from cloudshell.core.context.error_handling_context import ErrorHandlingContext
            with ErrorHandlingContext(shell_context.logger):
                from cloudshell.cp.aws.common.converters import convert_to_bool
                force = convert_to_bool(force)
                shell_context.logger.info('Detaching volume {1} from device {0}. Force: {2}'
                                          .format(device, volume_id, force))

                # Get instance id
                deployed_instance_id = \
                    self.aws_shell.model_parser.try_get_deployed_connected_resource_instance_id(context)

                # Get instance object
                instance = shell_context.aws_api.ec2_session.Instance(deployed_instance_id)

                # Detach volume
                instance.detach_volume(Device=device, VolumeId=volume_id, Force=force)

    @staticmethod
    def _instance_profile_associations_exists(result):
        return result and 'IamInstanceProfileAssociations' in result and len(
                result['IamInstanceProfileAssociations']) > 0

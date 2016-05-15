import jsonpickle
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface

from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder
from cloudshell.cp.aws.common.model_factory import ResourceModelParser
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel


class DeployAWSEC2AMIInstance(ResourceDriverInterface):
    def __init__(self):
        self.resource_model_parser = ResourceModelParser()

    def cleanup(self):
        pass

    def initialize(self, context):
        pass

    def Deploy(self, context, Name=None):
        # Create cloudshell session
        session = self.cs_helper.get_session(context.connectivity.server_address,
                                             context.connectivity.admin_auth_token,
                                             context.reservation.domain)

        # create deployment resource model and serialize it to json
        ## TODO Move this class to the core project  #
        ## TODO  Currently its duplicated in vcenter and in aws ##
        aws_ami_deployment_resource_model = \
            self.resource_model_parser.convert_to_resource_model(context.resource,
                                                                 DeployAWSEc2AMIInstanceResourceModel)

        ami_res_name = aws_ami_deployment_resource_model.device_name

        if not Name:
            Name = jsonpickle.decode(context.resource.app_context.app_request_json)['name']

        deployment_info = self._get_deployment_info(aws_ami_deployment_resource_model, Name)

        # call command on the AWS cloud privider
        result = session.ExecuteCommand(context.reservation.reservation_id,
                                        ami_res_name,
                                        "Resource",
                                        "deploy_ami",
                                        self._get_command_inputs_list(deployment_info),
                                        False)
        return result.Output


    def _get_deployment_info(self, image_model, name):
        """
        :type image_model: vCenterVMFromImageResourceModel
        """

        return DeployDataHolder({'app_name': name,
                                 'image_params': image_model
                                 })

import jsonpickle
from cloudshell.api.cloudshell_api import InputNameValue
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface

from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.common.deploy_data_holder import DeployDataHolder


class DeployAWSEC2AMIInstance(ResourceDriverInterface):
    def __init__(self):
        # Todo remove this to a common place outside the package
        self.cs_helper = CloudshellDriverHelper()

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
        aws_ami_deployment_resource_model = self._convert_context_to_deployment_resource_model(context.resource)
        aws_ami_deployment_resource_model.device_name = "/dev/sda1"
        aws_ami_deployment_resource_model.aws_key= "aws_testing_key_pair"


        ami_res_name = jsonpickle.decode(context.resource.app_context.app_request_json)['name']

        deployment_info = self._get_deployment_info(aws_ami_deployment_resource_model, ami_res_name)

        # call command on the AWS cloud privider
        result = session.ExecuteCommand(context.reservation.reservation_id,
                                        aws_ami_deployment_resource_model.aws_ec2,
                                        "Resource",
                                        "deploy_ami",
                                        self._get_command_inputs_list(deployment_info),
                                        False)
        return result.Output

    # todo: remove this to a common place
    def _convert_context_to_deployment_resource_model(self, resource):
        deployedResource = DeployAWSEc2AMIInstanceResourceModel()
        deployedResource.aws_ami_id = resource.attributes['AWS AMI Id']
        deployedResource.aws_ec2 = resource.attributes['AWS EC2']
        deployedResource.storage_iops = resource.attributes['Storage IOPS']
        deployedResource.storage_size = resource.attributes['Storage Size']
        deployedResource.instance_type = resource.attributes['Instance Type']


        return deployedResource

    def _get_deployment_info(self, image_model, name):
        """
        :type image_model: vCenterVMFromImageResourceModel
        """

        return DeployDataHolder({'app_name': name,
                                 'image_params': image_model
                                 })

    def _get_command_inputs_list(self, data_holder):
        return [InputNameValue('request', jsonpickle.encode(data_holder, unpicklable=False))]

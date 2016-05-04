from cloudshell.cp.aws.models.aws_ec2_datamodel import AWSEc2Datamodel


class DeployAMIOperation(object):
    def __init__(self, aws_api):
        """
        :param aws_api this is the...
        :type aws_api: cloudshell.cp.aws.device_access_layer.aws_api.AWSApi
        """
        self.aws_api = aws_api

    def deploy(self, ec2_session, aws_ec2_datamodel, ami_resource_model):
        """
        :param ec2_session:
        :param aws_ec2_datamodel:
        :type aws_ec2_datamodel : cloudshell.cp.aws.models.aws_ec2_datamodel.AWSEc2Datamodel
        :param ami_resource_model : the model of the AMI
        :type ami_resource_model: cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model.DeployAWSEc2AMIInstanceResourceModel
        :return:
        """
        aws_model=AWSEc2Datamodel()
        aws_model.aws_ami_id = aws_ec2_datamodel.aws_ami_id


        self.aws_api.create_instance(ec2_session,)
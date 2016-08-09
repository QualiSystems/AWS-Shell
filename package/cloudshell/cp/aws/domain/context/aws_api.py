from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider
from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel


class AwsApiSessionContext(object):
    def __init__(self, aws_session_manager, cloudshell_session, aws_ec2_resource_model):
        """
        Initializes an instance of AwsFullApiContext
        :param aws_session_manager:
        :type aws_session_manager: AWSSessionProvider
        :param cloudshell_session:
        :type: cloudshell_session: CloudShellAPISession
        :param aws_ec2_resource_model:
        :type aws_ec2_resource_model: AWSEc2CloudProviderResourceModel
        """
        self.aws_session_manager = aws_session_manager
        self.cloudshell_session = cloudshell_session
        self.aws_ec2_resource_model = aws_ec2_resource_model

    def __enter__(self):
        """
        Initializes all available aws api client and sessions
        :rtype: cloudshell.cp.aws.models.aws_api.AwsApiClients
        """
        return self.aws_session_manager.get_clients(cloudshell_session=self.cloudshell_session,
                                                    aws_ec2_data_model=self.aws_ec2_resource_model)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called upon end of the context. Does nothing
        :param exc_type: Exception type
        :param exc_val: Exception value
        :param exc_tb: Exception traceback
        :return:
        """
        pass

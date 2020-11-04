from cloudshell.core.context.error_handling_context import ErrorHandlingContext
from cloudshell.shell.core.session.cloudshell_session import CloudShellSessionContext
from cloudshell.shell.core.session.logging_session import LoggingSessionContext

from cloudshell.cp.aws.domain.context.aws_api import AwsApiSessionContext
from cloudshell.cp.aws.domain.context.aws_resource_model import AwsResourceModelContext
from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider


class AwsShellContext(object):
    def __init__(self, context, aws_session_manager):
        """
        Initializes an instance of AwsShellContext
        :param ResourceCommandContext context: Command context
        :param AWSSessionProvider aws_session_manager:
        """
        self.context = context
        self.aws_session_manager = aws_session_manager
        self.model_parser = AWSModelsParser()

    def __enter__(self):
        """
        Initializes all aws shell context dependencies
        :rtype AwsShellContextModel:
        """
        with LoggingSessionContext(self.context) as logger:
            with ErrorHandlingContext(logger):
                with CloudShellSessionContext(self.context) as cloudshell_session:
                    with AwsResourceModelContext(self.context, self.model_parser) as aws_ec2_resource_model:
                        with AwsApiSessionContext(aws_session_manager=self.aws_session_manager,
                                                  cloudshell_session=cloudshell_session,
                                                  aws_ec2_resource_model=aws_ec2_resource_model) as aws_api:
                            return AwsShellContextModel(logger=logger,
                                                        cloudshell_session=cloudshell_session,
                                                        aws_ec2_resource_model=aws_ec2_resource_model,
                                                        aws_api=aws_api)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Called upon end of the context. Does nothing
        :param exc_type: Exception type
        :param exc_val: Exception value
        :param exc_tb: Exception traceback
        :return:
        """
        pass


class AwsShellContextModel(object):
    def __init__(self, logger, cloudshell_session, aws_ec2_resource_model, aws_api):
        """
        :param logging.Logger logger:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell_session:
        :param cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel aws_ec2_resource_model:
        :param cloudshell.cp.aws.domain.context.aws_api.AwsApiClients aws_api:
        :return:
        """
        self.logger = logger
        self.cloudshell_session = cloudshell_session
        self.aws_ec2_resource_model = aws_ec2_resource_model
        self.aws_api = aws_api

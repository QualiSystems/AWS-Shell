from retrying import retry

from cloudshell.cp.aws.common.retry_helper import retry_if_client_error
from cloudshell.cp.aws.domain.common.list_helper import first_or_default
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.network_actions_models import DeployNetworkingResultModel
from cloudshell.cp.core.models import ConnectToSubnetParams


class ElasticIpService(object):
    def __init__(self):
        pass

    def set_elastic_ips(self, ec2_session, ec2_client, instance, ami_deployment_model, network_actions, network_config_results, logger):
        """

        :param ec2_session: EC2 session
        :param ec2_client: EC2 client
        :param instance:
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param cloudshell.cp.core.models.ConnectSubnet network_actions:
        :param list[DeployNetworkingResultModel] network_config_results:
        :param logging.Logger logger:
        :return:
        """
        if not ami_deployment_model.allocate_elastic_ip:
            return

        if self._is_single_subnet_mode(network_actions):
            elastic_ip = self.allocate_elastic_address(ec2_client=ec2_client)
            network_config_results[0].public_ip = elastic_ip  # set elastic ip data in deploy result
            network_config_results[0].is_elastic_ip = True
            self.associate_elastic_ip_to_instance(ec2_session=ec2_session,
                                                  instance=instance,
                                                  elastic_ip=elastic_ip)
            logger.info("Single subnet mode detected. Allocated & associated elastic ip {0} to instance {1}"
                        .format(elastic_ip, instance.id))
            return

        # allocate elastic ip for each interface inside a public subnet
        for action in network_actions:
            if not isinstance(action.actionParams, ConnectToSubnetParams) \
                    or not action.actionParams.isPublic:
                continue

            # find network interface using device index
            action_result = first_or_default(network_config_results, lambda x: x.action_id == action.actionId)
            interface = filter(lambda x: x["Attachment"]["DeviceIndex"] == action_result.device_index,
                               instance.network_interfaces_attribute)[0]

            # allocate and assign elastic ip
            elastic_ip = self.allocate_elastic_address(ec2_client=ec2_client)
            action_result.public_ip = elastic_ip  # set elastic ip data in deploy result
            action_result.is_elastic_ip = True
            interface_id = interface["NetworkInterfaceId"]
            self.associate_elastic_ip_to_network_interface(ec2_session=ec2_session,
                                                           interface_id=interface_id,
                                                           elastic_ip=elastic_ip)
            logger.info("Multi-subnet mode detected. Allocated & associated elastic ip {0} to interface {1}"
                        .format(elastic_ip, interface_id))

    def _is_single_subnet_mode(self, network_actions):
        # todo move code to networking service
        return network_actions is None or \
               (isinstance(network_actions, list) and
                len(network_actions) <= 1)

    @retry(retry_on_exception=retry_if_client_error, stop_max_attempt_number=30, wait_fixed=1000)
    def associate_elastic_ip_to_instance(self, ec2_session, instance, elastic_ip):
        """
        Assign an elastic ip to the primary interface and primary private ip of the given instance
        :param ec2_session:
        :param instance:
        :param str elastic_ip: The allocation ID
        :return:
        """
        response = list(ec2_session.vpc_addresses.filter(PublicIps=[elastic_ip]))
        if len(response) == 1:
            vpc_address = response[0]
            vpc_address.associate(InstanceId=instance.id, AllowReassociation=False)
        else:
            raise ValueError("Failed to find elastic ip {0} allocation id".format(elastic_ip))

    @retry(retry_on_exception=retry_if_client_error, stop_max_attempt_number=30, wait_fixed=1000)
    def associate_elastic_ip_to_network_interface(self, ec2_session, interface_id, elastic_ip):
        """
        Assign an elastic ip to a specific network interface
        :param ec2_session:
        :param str interface_id:
        :param str elastic_ip: The allocation ID
        :return:
        """
        response = list(ec2_session.vpc_addresses.filter(PublicIps=[elastic_ip]))
        if len(response) == 1:
            vpc_address = response[0]
            vpc_address.associate(NetworkInterfaceId=interface_id, AllowReassociation=False)
        else:
            raise ValueError("Failed to find elastic ip {0} allocation id".format(elastic_ip))

    def allocate_elastic_address(self, ec2_client):
        """
        :param ec2_client:
        :return: allocated elastic ip
        :rtype: str
        """
        result = ec2_client.allocate_address(Domain='vpc')
        return result["PublicIp"]

    @retry(retry_on_exception=retry_if_client_error, stop_max_attempt_number=30, wait_fixed=1000)
    def find_and_release_elastic_address(self, ec2_session, elastic_ip):
        """
        :param ec2_session:
        :param str elastic_ip:
        """
        response = list(ec2_session.vpc_addresses.filter(PublicIps=[elastic_ip]))
        if len(response) == 1:
            vpc_address = response[0]
            self.release_elastic_address(vpc_address)
        else:
            raise ValueError("Failed to find elastic ip {0}".format(elastic_ip))

    def release_elastic_address(self, vpc_address):
        """
        :param vpc_address:
        """
        vpc_address.release()

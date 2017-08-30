from cloudshell.cp.aws.domain.common.list_helper import first_or_default
from cloudshell.cp.aws.models.deploy_aws_ec2_ami_instance_resource_model import DeployAWSEc2AMIInstanceResourceModel
from cloudshell.cp.aws.models.network_actions_models import DeployNetworkingResultModel, SubnetConnectionParams


class ElasticIpService(object):
    def __init__(self):
        pass

    def set_elastic_ips(self, ec2_session, ec2_client, instance, ami_deployment_model, network_config_results):
        """

        :param ec2_session: EC2 session
        :param ec2_client: EC2 client
        :param instance:
        :param DeployAWSEc2AMIInstanceResourceModel ami_deployment_model:
        :param list[DeployNetworkingResultModel] network_config_results:
        :return:
        """
        if not ami_deployment_model.allocate_elastic_ip:
            return

        if self._is_single_subnet_mode(ami_deployment_model):
            elastic_ip = self.allocate_elastic_address(ec2_client=ec2_client)
            network_config_results[0].public_ip = elastic_ip  # set elastic ip data in deploy result
            self.associate_elastic_ip_to_instance(ec2_session=ec2_session,
                                                  instance=instance,
                                                  elastic_ip=elastic_ip)

            return

        # allocate elastic ip for each interface inside a public subnet
        for action in ami_deployment_model.network_configurations:
            if not isinstance(action.connection_params, SubnetConnectionParams) \
                    or not action.connection_params.is_public_subnet():
                continue

            # find network interface using device index
            action_result = first_or_default(network_config_results, lambda x: x.action_id == action.id)
            interface = filter(lambda x: x["Attachment"]["DeviceIndex"] == action_result.device_index,
                               instance.network_interfaces_attribute)[0]

            # allocate and assign elastic ip
            elastic_ip = self.allocate_elastic_address(ec2_client=ec2_client)
            action_result.public_ip = elastic_ip  # set elastic ip data in deploy result
            self.associate_elastic_ip_to_network_interface(ec2_session=ec2_session,
                                                           interface_id=interface["NetworkInterfaceId"],
                                                           elastic_ip=elastic_ip)

    def _is_single_subnet_mode(self, ami_deployment_model):
        # todo move code to networking service
        return ami_deployment_model.network_configurations is None or \
               (isinstance(ami_deployment_model.network_configurations, list) and
                len(ami_deployment_model.network_configurations) == 1)

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

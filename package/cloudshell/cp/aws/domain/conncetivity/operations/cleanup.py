import traceback

from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel


class CleanupConnectivityOperation(object):
    def __init__(self, vpc_service, key_pair_service, route_table_service):
        """
        :param vpc_service: VPC Service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc.VPCService
        :param key_pair_service: Security Group Service
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        :param route_table_service:
        :type route_table_service: cloudshell.cp.aws.domain.services.ec2.route_table.RouteTablesService
        """
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service
        self.route_table_service = route_table_service

    def cleanup(self, ec2_session, s3_session, aws_ec2_data_model, reservation_id, logger):
        """
        :param ec2_session:
        :param s3_session:
        :param AWSEc2CloudProviderResourceModel aws_ec2_data_model: The AWS EC2 data model
        :param str reservation_id:
        :param logging.Logger logger:
        :return:
        """
        result = {'success': True}
        try:
            vpc = self.vpc_service.find_vpc_for_reservation(ec2_session, reservation_id)
            if not vpc:
                raise ValueError('No VPC was created for this reservation')

            logger.info("Deleting all instances")
            self.vpc_service.delete_all_instances(vpc)

            logger.info("Removing private key (pem file) from s3")
            self.key_pair_service.remove_key_pair_for_reservation_in_s3(s3_session,
                                                                        aws_ec2_data_model.key_pairs_location,
                                                                        reservation_id)
            logger.info("Removing key pair from ec2")
            self.key_pair_service.remove_key_pair_for_reservation_in_ec2(ec2_session=ec2_session,
                                                                         reservation_id=reservation_id)

            logger.info("Deleting vpc and removing dependencies")
            self.vpc_service.remove_all_internet_gateways(vpc)
            self.vpc_service.remove_all_security_groups(vpc)
            self.vpc_service.remove_all_subnets(vpc)
            self.vpc_service.remove_all_peering(vpc)
            self._delete_blackhole_routes_in_vpc_route_table(ec2_session, aws_ec2_data_model)

            self.vpc_service.delete_vpc(vpc)
        except Exception as exc:
            logger.error("Error in cleanup connectivity. Error: {0}".format(traceback.format_exc()))
            result['success'] = False
            result['errorMessage'] = 'CleanupConnectivity ended with the error: {0}'.format(exc)

        return result

    def _delete_blackhole_routes_in_vpc_route_table(self, ec2_session, aws_ec2_data_model):
        rt = self.route_table_service.get_main_route_table(ec2_session, aws_ec2_data_model.aws_management_vpc_id)
        self.route_table_service.delete_blackhole_routes(rt)

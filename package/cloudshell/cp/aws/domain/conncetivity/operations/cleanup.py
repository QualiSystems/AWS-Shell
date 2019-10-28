import traceback

from cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model import AWSEc2CloudProviderResourceModel
from cloudshell.cp.core.models import CleanupNetwork


class CleanupSandboxInfraOperation(object):
    def __init__(self, vpc_service, key_pair_service, route_table_service, traffic_mirror_service):
        """
        :param vpc_service: VPC Service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc.VPCService
        :param key_pair_service: Security Group Service
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        :param route_table_service:
        :type route_table_service: cloudshell.cp.aws.domain.services.ec2.route_table.RouteTablesService
        :param cloudshell.cp.aws.domain.services.ec2.mirroring.TrafficMirrorService traffic_mirror_service:
        """
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service
        self.route_table_service = route_table_service
        self.traffic_mirror_service = traffic_mirror_service

    def cleanup(self, ec2_client, ec2_session, s3_session, aws_ec2_data_model, reservation_id, actions, logger):
        """
        :param ec2_client:
        :param ec2_session:
        :param s3_session:
        :param AWSEc2CloudProviderResourceModel aws_ec2_data_model: The AWS EC2 data model
        :param str reservation_id:
        :param list[NetworkAction] actions:
        :param logging.Logger logger:
        :return:
        """
        if not actions:
            raise ValueError("No cleanup action was found")

        result = CleanupNetwork()
        result.actionId = actions[0].actionId
        result.success = True

        try:
            # need to remove the keypair before we try to find the VPC
            self._remove_keypair(aws_ec2_data_model, ec2_session, logger, reservation_id, s3_session)
            vpc = self.vpc_service.find_vpc_for_reservation(ec2_session, reservation_id)

            if not vpc:
                raise ValueError('No VPC was created for this reservation')

            logger.info("Deleting all instances")
            self.vpc_service.delete_all_instances(vpc)

            logger.info("Deleting vpc and removing dependencies")
            self.vpc_service.remove_all_internet_gateways(vpc)
            self.vpc_service.remove_all_security_groups(vpc, reservation_id)
            self.vpc_service.remove_all_subnets(vpc)
            self.vpc_service.remove_all_peering(vpc)
            self._delete_blackhole_routes_in_vpc_route_table(ec2_session, ec2_client, aws_ec2_data_model)
            self.vpc_service.remove_custom_route_tables(ec2_session, vpc)

            logger.info('Deleting traffic mirror elements')
            self.vpc_service.delete_traffic_mirror_elements(ec2_client, self.traffic_mirror_service, reservation_id,
                                                            logger)

            self.vpc_service.delete_vpc(vpc)


            
        except Exception as exc:
            logger.error("Error in cleanup connectivity. Error: {0}".format(traceback.format_exc()))
            result.success = False
            result.errorMessage = 'CleanupSandboxInfra ended with the error: {0}'.format(exc)
        return result

    def _remove_keypair(self, aws_ec2_data_model, ec2_session, logger, reservation_id, s3_session):
        logger.info("Removing private key (pem file) from s3")
        self.key_pair_service.remove_key_pair_for_reservation_in_s3(s3_session,
                                                                    aws_ec2_data_model.key_pairs_location,
                                                                    reservation_id)
        logger.info("Removing key pair from ec2")
        self.key_pair_service.remove_key_pair_for_reservation_in_ec2(ec2_session=ec2_session,
                                                                     reservation_id=reservation_id)

    def _delete_blackhole_routes_in_vpc_route_table(self, ec2_session, ec2_client, aws_ec2_data_model):
        rts = self.route_table_service.get_all_route_tables(ec2_session=ec2_session,
                                                            vpc_id=aws_ec2_data_model.aws_management_vpc_id)
        for rt in rts:
            self.route_table_service.delete_blackhole_routes(rt, ec2_client)

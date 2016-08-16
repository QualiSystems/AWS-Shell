import traceback

from cloudshell.cp.aws.domain.services.ec2 import route_table
from cloudshell.cp.aws.domain.services.ec2.tags import *
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter
from cloudshell.cp.aws.models.connectivity_models import PrepareConnectivityActionResult
from cloudshell.cp.aws.models.port_data import PortData

INVALID_REQUEST_ERROR = 'Invalid request: {0}'


class PrepareConnectivityOperation(object):
    def __init__(self, vpc_service, security_group_service, key_pair_service, tag_service, route_table_service):
        """
        :param vpc_service: VPC Service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc.VPCService
        :param security_group_service:
        :type security_group_service: clousdhell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :param key_pair_service:
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        :param tag_service:
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        :param route_table_service:
        :type route_table_service: cloudshell.cp.aws.domain.services.ec2.route_table.RouteTablesService
        """
        self.vpc_service = vpc_service
        self.security_group_service = security_group_service
        self.key_pair_service = key_pair_service
        self.tag_service = tag_service
        self.route_table_service = route_table_service

    def prepare_connectivity(self, ec2_client, ec2_session, s3_session, reservation, aws_ec2_datamodel, request, logger):
        """
        Will create a vpc for the reservation and will peer it to the management vpc
        also will create a key pair for that reservation
        :param ec2_client: ec2 client
        :param ec2_session: EC2 Session
        :param s3_session: S3 Session
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param aws_ec2_datamodel: The AWS EC2 data model
        :type aws_ec2_datamodel: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param request: Parsed prepare connectivity request
        :param logging.Logger logger:
        :return:
        """
        if not aws_ec2_datamodel.aws_management_vpc_id:
            raise ValueError('AWS Mgmt VPC ID attribute must be set!')

        logger.info("Creating or getting existing key pair")
        self._create_key_pair(ec2_session=ec2_session,
                              s3_session=s3_session,
                              bucket=aws_ec2_datamodel.key_pairs_location,
                              reservation_id=reservation.reservation_id)
        results = []
        for action in request.actions:
            try:
                cidr = self._extract_cidr(action)
                logger.info("Received CIDR {0} from server".format(cidr))

                # will get or create a vpc for the reservation
                logger.info("Get or create existing VPC")
                vpc = self._get_or_create_vpc(cidr, ec2_session, reservation)

                # will create an IG if not exist
                logger.info("Get or create and attach existing internet gateway")
                internet_gateway_id = self._create_and_attach_internet_gateway(ec2_session, vpc, reservation)

                # will try to peer sandbox VPC to mgmt VPC if not exist
                logger.info("Create VPC Peering with management vpc")
                self._peer_vpcs(ec2_client=ec2_client,
                                ec2_session=ec2_session,
                                management_vpc_id=aws_ec2_datamodel.aws_management_vpc_id,
                                vpc_id=vpc.id,
                                sandbox_vpc_cidr=cidr,
                                internet_gateway_id=internet_gateway_id,
                                reservation_model=reservation,
                                logger=logger)

                logger.info("Get or create default Security Group")
                security_group = self._get_or_create_security_group(ec2_session=ec2_session,
                                                                    reservation=reservation,
                                                                    vpc=vpc,
                                                                    management_sg_id=aws_ec2_datamodel.aws_management_sg_id)

                results.append(self._create_action_result(action, security_group, vpc))

            except Exception as e:
                logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
                results.append(self._create_fault_action_result(action, e))
        return results

    def _create_key_pair(self, ec2_session, s3_session, bucket, reservation_id):
        keypair = self.key_pair_service.get_key_for_reservation(s3_session=s3_session,
                                                                bucket_name=bucket,
                                                                reservation_id=reservation_id)
        if not keypair:
            self.key_pair_service.create_key_pair(ec2_session=ec2_session,
                                                  s3_session=s3_session,
                                                  bucket=bucket,
                                                  reservation_id=reservation_id)

    def _peer_vpcs(self, ec2_client, ec2_session, management_vpc_id, vpc_id, sandbox_vpc_cidr, internet_gateway_id,
                   reservation_model, logger):
        """
        :param ec2_client
        :param ec2_session:
        :param management_vpc_id:
        :param vpc_id:
        :param sandbox_vpc_cidr:
        :param internet_gateway_id:
        :param reservation_model:
        :param logging.Logger logger:
        :return:
        """
        # check if a peering connection already exist
        vpc_peer_connection_id = None
        peerings = \
            self.vpc_service.get_peering_connection_by_reservation_id(ec2_session, reservation_model.reservation_id)
        if peerings:
            active_peerings = filter(lambda x: x.status['Code'] == VpcPeeringConnectionWaiter.ACTIVE, peerings)
            if active_peerings:
                vpc_peer_connection_id = active_peerings[0].id

        if not vpc_peer_connection_id:
            # create vpc peering connection
            vpc_peer_connection_id = self.vpc_service.peer_vpcs(ec2_session=ec2_session,
                                                                vpc_id1=management_vpc_id,
                                                                vpc_id2=vpc_id,
                                                                reservation_model=reservation_model)
        # get mgmt vpc cidr
        mgmt_cidr = self.vpc_service.get_vpc_cidr(ec2_session=ec2_session, vpc_id=management_vpc_id)

        # add route in management route table to the new sandbox vpc
        mgmt_route_table = self.route_table_service.get_main_route_table(ec2_session=ec2_session,
                                                                         vpc_id=management_vpc_id)
        self._update_route_to_peered_vpc(peer_connection_id=vpc_peer_connection_id,
                                         route_table=mgmt_route_table,
                                         target_vpc_cidr=sandbox_vpc_cidr,
                                         logger=logger,
                                         ec2_session=ec2_session,
                                         ec2_client=ec2_client)

        # add route in sandbox route table to the management vpc
        sandbox_route_table = self.route_table_service.get_main_route_table(ec2_session=ec2_session,
                                                                            vpc_id=vpc_id)
        self._update_route_to_peered_vpc(peer_connection_id=vpc_peer_connection_id,
                                         route_table=sandbox_route_table,
                                         target_vpc_cidr=mgmt_cidr,
                                         logger=logger,
                                         ec2_session=ec2_session,
                                         ec2_client=ec2_client)

        # add route in sandbox route table to the internet gateway
        route_igw = self.route_table_service.find_first_route(sandbox_route_table, {'gateway_id': internet_gateway_id})
        if not route_igw:
            self.route_table_service.add_route_to_internet_gateway(route_table=sandbox_route_table,
                                                                   target_internet_gateway_id=internet_gateway_id)

    @retry(stop_max_attempt_number=2, wait_fixed=1000)
    def _update_route_to_peered_vpc(self, ec2_client, ec2_session, route_table, peer_connection_id,
                                    target_vpc_cidr, logger):
        """
        :param ec2_client:
        :param ec2_session:
        :param route_table:
        :param peer_connection_id:
        :param target_vpc_cidr:
        :param logging.Logger logger:
        :return:
        """
        logger.info("_update_route_to_peered_vpc :: route table id {0}, peer_connection_id: {1}, target_vpc_cidr: {2}"
                    .format(route_table.id, peer_connection_id, target_vpc_cidr))

        # need to check for both possibilities since the amazon api for Route is unpredictable
        route = self.route_table_service.find_first_route(route_table, {'destination_cidr_block': str(target_vpc_cidr)})
        if not route:
            route = self.route_table_service.find_first_route(route_table, {'DestinationCidrBlock': str(target_vpc_cidr)})

        if route:
            logger.info("_update_route_to_peered_vpc :: found route to {0}, replacing it")
            self.route_table_service.replace_route(route_table=route_table,
                                                   route=route,
                                                   peer_connection_id=peer_connection_id,
                                                   ec2_client=ec2_client)
        else:
            logger.info("_update_route_to_peered_vpc :: route not found, creating it")
            self.route_table_service.add_route_to_peered_vpc(route_table=route_table,
                                                             target_peering_id=peer_connection_id,
                                                             target_vpc_cidr=target_vpc_cidr)

    def _get_or_create_security_group(self, ec2_session, reservation, vpc, management_sg_id):
        sg_name = self.security_group_service.get_sandbox_security_group_name(reservation.reservation_id)
        security_group = self.security_group_service.get_security_group_by_name(vpc=vpc, name=sg_name)

        if not security_group:
            security_group = \
                self.security_group_service.create_security_group(ec2_session=ec2_session,
                                                                  vpc_id=vpc.id,
                                                                  security_group_name=sg_name)

            tags = self.tag_service.get_security_group_tags(name=sg_name,
                                                            isolation=IsolationTagValues.Shared,
                                                            reservation=reservation)
            self.tag_service.set_ec2_resource_tags(security_group, tags)

            self.security_group_service.set_shared_reservation_security_group_rules(security_group=security_group,
                                                                                    management_sg_id=management_sg_id)

        return security_group

    def _get_or_create_vpc(self, cidr, ec2_session, reservation):
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                        reservation_id=reservation.reservation_id)
        if not vpc:
            vpc = self.vpc_service.create_vpc_for_reservation(ec2_session=ec2_session,
                                                              reservation=reservation,
                                                              cidr=cidr)
        return vpc

    @staticmethod
    def _create_action_result(action, security_group, vpc):
        action_result = PrepareConnectivityActionResult()
        action_result.actionId = action.actionId
        action_result.success = True
        action_result.infoMessage = 'PrepareConnectivity finished successfully'
        action_result.vpcId = vpc.id
        action_result.securityGroupId = security_group.id
        return action_result

    @staticmethod
    def _extract_cidr(action):
        cidrs = [custom_attribute.attributeValue
                 for custom_attribute in action.customActionAttributes
                 if custom_attribute.attributeName == 'Network']
        if not cidrs:
            raise ValueError(INVALID_REQUEST_ERROR.format('CIDR is missing'))
        if len(cidrs) > 1:
            raise ValueError(INVALID_REQUEST_ERROR.format('Too many CIDRs parameters were found'))
        return cidrs[0]

    @staticmethod
    def _create_fault_action_result(action, e):
        action_result = PrepareConnectivityActionResult()
        action_result.actionId = action.actionId
        action_result.success = False
        action_result.errorMessage = 'PrepareConnectivity ended with the error: {0}'.format(e)
        return action_result

    @retry(stop_max_attempt_number=3, wait_fixed=1000)
    def _create_and_attach_internet_gateway(self, ec2_session, vpc, reservation):
        """
        :param ec2_session:
        :param vpc:
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :return:
        """

        # check if internet gateway is not already attached
        all_internet_gateways = self.vpc_service.get_all_internet_gateways(vpc)
        if len(all_internet_gateways) > 0:
            return all_internet_gateways[0].id

        return self.vpc_service.create_and_attach_internet_gateway(ec2_session, vpc, reservation)

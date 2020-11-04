import traceback

import jsonpickle
from cloudshell.shell.core.driver_context import CancellationContext

from cloudshell.cp.aws.domain.conncetivity.operations.prepare_subnet_executor import PrepareSubnetExecutor, \
    SubnetActionHelper
from cloudshell.cp.aws.domain.services.ec2.tags import *
from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter
from cloudshell.cp.core.models import PrepareCloudInfra
from cloudshell.cp.core.models import PrepareSubnet
from cloudshell.cp.core.models import CreateKeys
from cloudshell.cp.core.models import CreateKeysActionResult
from cloudshell.cp.core.models import ActionResultBase
from cloudshell.cp.core.models import PrepareSubnetActionResult
from cloudshell.cp.core.models import PrepareCloudInfraResult
INVALID_REQUEST_ERROR = 'Invalid request: {0}'


class PrepareSandboxInfraOperation(object):
    def __init__(self, vpc_service, security_group_service, key_pair_service, tag_service, route_table_service,
                 cancellation_service, subnet_service, subnet_waiter):
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
        :param cancellation_service:
        :type cancellation_service: cloudshell.cp.aws.domain.common.cancellation_service.CommandCancellationService
        :param subnet_service: Subnet Service
        :type subnet_service: cloudshell.cp.aws.domain.services.ec2.subnet.SubnetService
        :param subnet_waiter: Subnet Waiter
        :type subnet_waiter: cloudshell.cp.aws.domain.services.waiters.subnet.SubnetWaiter
        """
        self.vpc_service = vpc_service
        self.security_group_service = security_group_service
        self.key_pair_service = key_pair_service
        self.tag_service = tag_service
        self.route_table_service = route_table_service
        self.cancellation_service = cancellation_service
        self.subnet_service = subnet_service
        self.subnet_waiter = subnet_waiter

    def prepare_connectivity(self, ec2_client, ec2_session, s3_session, reservation, aws_ec2_datamodel, actions,
                             cancellation_context, logger):
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
        :param list[RequestActionBase] actions: Parsed prepare connectivity actions
        :param CancellationContext cancellation_context:
        :param logging.Logger logger:
        :rtype list[ActionResultBase]
        """
        if not aws_ec2_datamodel.aws_management_vpc_id:
            raise ValueError('AWS Mgmt VPC ID attribute must be set!')

        logger.info("PrepareSandboxInfra actions: {0}".format(','.join([jsonpickle.encode(a) for a in actions])))
        results = []

        # Execute PrepareCloudInfra action first
        network_action = next((a for a in actions if isinstance(a, PrepareCloudInfra)), None)
        create_keys_action = next((a for a in actions if isinstance(a, CreateKeys)), None)
        if not network_action:
            raise ValueError("Actions list must contain a PrepareCloudInfraAction.")
        if not create_keys_action:
            raise ValueError("Actions list must contain a CreateKeys.")

        try:
            result = self._prepare_network(ec2_client, ec2_session, reservation, aws_ec2_datamodel,
                                           network_action, cancellation_context, logger)
            results.append(result)
        except Exception as e:
            logger.error("Error in prepare connectivity. Error: {0}".format(traceback.format_exc()))
            results.append(self._create_fault_action_result(network_action, e))
        try:
            result = self._prepare_key(ec2_session, s3_session, aws_ec2_datamodel, reservation, create_keys_action,
                                       logger)
            results.append(result)
        except Exception as e:
            logger.error("Error in prepare key. Error: {0}".format(traceback.format_exc()))
            results.append(self._create_fault_action_result(create_keys_action, e))

        # Execute prepareSubnet actions
        subnet_actions = [a for a in actions if isinstance(a, PrepareSubnet)]
        subnet_results = PrepareSubnetExecutor(
            cancellation_service=self.cancellation_service,
            vpc_service=self.vpc_service,
            subnet_service=self.subnet_service,
            tag_service=self.tag_service,
            subnet_waiter=self.subnet_waiter,
            reservation=reservation,
            aws_ec2_datamodel=aws_ec2_datamodel,
            cancellation_context=cancellation_context,
            logger=logger,
            ec2_session=ec2_session,
            ec2_client=ec2_client).execute(subnet_actions)

        for subnet_result in subnet_results:
            results.append(subnet_result)

        self.cancellation_service.check_if_cancelled(cancellation_context)
        logger.info("Prepare Connectivity completed")

        return results

    def _prepare_key(self, ec2_session, s3_session, aws_ec2_datamodel, reservation, action, logger):
        logger.info("Get or create existing key pair")
        access_key = self._get_or_create_key_pair(ec2_session=ec2_session,
                                                  s3_session=s3_session,
                                                  bucket=aws_ec2_datamodel.key_pairs_location,
                                                  reservation_id=reservation.reservation_id)
        return self._create_prepare_create_keys_result(action, access_key)

    def _prepare_network(self, ec2_client, ec2_session, reservation, aws_ec2_datamodel, action, cancellation_context,
                         logger):
        """
        :param ec2_client:
        :param ec2_session:
        :param reservation:
        :param aws_ec2_datamodel:
        :param PrepareCloudInfra action: NetworkAction
        :param CancellationContext cancellation_context:
        :param logging.Logger logger:
        :return:
        """
        logger.info("PrepareCloudInfra")

        # will get cidr form action params
        cidr = self._get_vpc_cidr(action, aws_ec2_datamodel, logger) or action.actionParams.cidr
        logger.info("Received CIDR {0} from server".format(cidr))

        # will get or create a vpc for the reservation
        self.cancellation_service.check_if_cancelled(cancellation_context)
        logger.info("Get or create existing VPC (no subnets yet)")
        vpc = self._get_or_create_vpc(cidr, ec2_session, reservation)

        # will enable dns for the vpc
        self.cancellation_service.check_if_cancelled(cancellation_context)
        logger.info("Enable dns for the vpc")
        self._enable_dns_hostnames(ec2_client=ec2_client, vpc_id=vpc.id)

        # will get or create an Internet-Gateway (IG) for the vpc
        self.cancellation_service.check_if_cancelled(cancellation_context)
        logger.info("Get or create and attach existing internet gateway")
        internet_gateway_id = self._create_and_attach_internet_gateway(ec2_session, vpc, reservation)

        # will try to peer sandbox VPC to mgmt VPC if not exist
        # note, if vpc_mode == static, will not create peering
        self._peer_to_mgmt_if_needed(aws_ec2_datamodel, cancellation_context, cidr, ec2_client, ec2_session,
                                     internet_gateway_id, logger, reservation, vpc)

        # will get or create default Security Group
        self.cancellation_service.check_if_cancelled(cancellation_context)
        logger.info("Get or create default Security Group")
        security_groups = \
            self._get_or_create_default_security_groups(ec2_session=ec2_session,
                                                        reservation=reservation,
                                                        vpc=vpc,
                                                        management_sg_id=aws_ec2_datamodel.aws_management_sg_id,
                                                        need_management_access=not aws_ec2_datamodel.is_static_vpc_mode)
        return self._create_prepare_network_result(action, security_groups, vpc)

    def _get_vpc_cidr(self, action, aws_ec2_datamodel, logger):
        if aws_ec2_datamodel.is_static_vpc_mode and aws_ec2_datamodel.vpc_cidr != '':
            cidr = aws_ec2_datamodel.vpc_cidr
            logger.info('Decided to use VPC CIDR {} as defined on cloud provider for sandbox VPC'
                        .format(cidr))
        else:
            cidr = action.actionParams.cidr
            logger.info("Received CIDR {0} from server".format(cidr))
        return cidr

    def _peer_to_mgmt_if_needed(self, aws_ec2_datamodel, cancellation_context, cidr, ec2_client, ec2_session,
                                internet_gateway_id, logger, reservation, vpc):
        self.cancellation_service.check_if_cancelled(cancellation_context)

        self.route_to_internet_gateway(ec2_session, internet_gateway_id, reservation, vpc.id)

        # add route in sandbox *private* route table to the management vpc
        sandbox_private_route_table = self.vpc_service.get_or_create_private_route_table(ec2_session, reservation,
                                                                                         vpc.id)

        if not aws_ec2_datamodel.is_static_vpc_mode:
            logger.info("Create VPC Peering with management vpc")
            self._peer_vpcs(ec2_client=ec2_client,
                            ec2_session=ec2_session,
                            management_vpc_id=aws_ec2_datamodel.aws_management_vpc_id,
                            vpc_id=vpc.id,
                            sandbox_vpc_cidr=cidr,
                            reservation_model=reservation,
                            logger=logger)
        else:
            logger.info("We are using static VPC mode, not creating VPC peering with management vpc")

    @retry(stop_max_attempt_number=30, wait_fixed=1000)
    def _enable_dns_hostnames(self, ec2_client, vpc_id):
        """

        :param ec2_client:
        :param vpc_id:
        :return:
        """
        self.vpc_service.modify_vpc_attribute(ec2_client=ec2_client, vpc_id=vpc_id, enable_dns_hostnames=True)

    def _get_or_create_key_pair(self, ec2_session, s3_session, bucket, reservation_id):
        """
        The method creates a keypair or retrieves an existing keypair and returns the private key.
        :param ec2_session:
        :param s3_session:
        :param str bucket:
        :param str reservation_id:
        :return: Private Key
        """
        private_key = self.key_pair_service.load_key_pair_by_name(s3_session=s3_session,
                                                                  bucket_name=bucket,
                                                                  reservation_id=reservation_id)
        if not private_key:
            key_pair = self.key_pair_service.create_key_pair(ec2_session=ec2_session,
                                                             s3_session=s3_session,
                                                             bucket=bucket,
                                                             reservation_id=reservation_id)
            private_key = key_pair.key_material

        return private_key

    def _peer_vpcs(self,
                   ec2_client,
                   ec2_session,
                   management_vpc_id,
                   vpc_id,
                   sandbox_vpc_cidr,
                   reservation_model,
                   logger):
        """
        :param ec2_client
        :param ec2_session:
        :param management_vpc_id:
        :param vpc_id:
        :param sandbox_vpc_cidr:
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
                                                                reservation_model=reservation_model,
                                                                logger=logger)
        # get mgmt vpc cidr
        mgmt_cidr = self.vpc_service.get_vpc_cidr(ec2_session=ec2_session, vpc_id=management_vpc_id)

        # add route in mgmgt vpc for ALL route tables to the new sandbox vpc
        mgmt_rts = self.route_table_service.get_all_route_tables(ec2_session=ec2_session, vpc_id=management_vpc_id)
        for mgmt_route_table in mgmt_rts:
            self._update_route_to_peered_vpc(peer_connection_id=vpc_peer_connection_id,
                                             route_table=mgmt_route_table,
                                             target_vpc_cidr=sandbox_vpc_cidr,
                                             logger=logger,
                                             ec2_session=ec2_session,
                                             ec2_client=ec2_client)

        # add route in sandbox route table to the management vpc
        sandbox_main_route_table = self.route_table_service.get_main_route_table(ec2_session=ec2_session,
                                                                                 vpc_id=vpc_id)
        self._update_route_to_peered_vpc(peer_connection_id=vpc_peer_connection_id,
                                         route_table=sandbox_main_route_table,
                                         target_vpc_cidr=mgmt_cidr,
                                         logger=logger,
                                         ec2_session=ec2_session,
                                         ec2_client=ec2_client)

        # add route in sandbox *private* route table to the management vpc
        sandbox_private_route_table = self.vpc_service.get_or_create_private_route_table(ec2_session, reservation_model, vpc_id)

        self._update_route_to_peered_vpc(peer_connection_id=vpc_peer_connection_id,
                                         route_table=sandbox_private_route_table,
                                         target_vpc_cidr=mgmt_cidr,
                                         logger=logger,
                                         ec2_session=ec2_session,
                                         ec2_client=ec2_client)

    def route_to_internet_gateway(self, ec2_session, internet_gateway_id, reservation_model, vpc_id):
        # add route in sandbox route table to the internet gateway
        # ***DO NOT ADD IT TO sandbox_private_route_table!***
        sandbox_main_route_table = self.route_table_service.get_main_route_table(ec2_session=ec2_session,
                                                                                 vpc_id=vpc_id)
        route_igw = self.route_table_service.find_first_route(sandbox_main_route_table,
                                                              {'gateway_id': internet_gateway_id})
        if not route_igw:
            self.route_table_service.add_route_to_internet_gateway(route_table=sandbox_main_route_table,
                                                                   target_internet_gateway_id=internet_gateway_id)
        # add default tags to main routing table
        self.vpc_service.set_main_route_table_tags(sandbox_main_route_table, reservation_model)

    @retry(stop_max_attempt_number=30, wait_fixed=1000)
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
        logger.info("route table id {0}, peer_connection_id: {1}, target_vpc_cidr: {2}"
                    .format(route_table.id, peer_connection_id, target_vpc_cidr))

        # need to check for both possibilities since the amazon api for Route is unpredictable
        route = self.route_table_service.find_first_route(route_table, {'destination_cidr_block': str(target_vpc_cidr)})
        if not route:
            route = self.route_table_service.find_first_route(route_table,
                                                              {'DestinationCidrBlock': str(target_vpc_cidr)})

        if route:
            if hasattr(route, "vpc_peering_connection_id") and route.vpc_peering_connection_id == peer_connection_id:
                logger.info("found existing and valid route to peering gateway, no need to update it")
                return  # the existing route is correct, we dont need to do anything

            logger.info("found existing route to {0}, replacing it".format(
                route.destination_cidr_block if hasattr(route, "destination_cidr_block") else ''))
            self.route_table_service.replace_route(route_table=route_table,
                                                   route=route,
                                                   peer_connection_id=peer_connection_id,
                                                   ec2_client=ec2_client)
        else:
            logger.info("route not found, creating it")
            self.route_table_service.add_route_to_peered_vpc(route_table=route_table,
                                                             target_peering_id=peer_connection_id,
                                                             target_vpc_cidr=target_vpc_cidr)

    def _get_or_create_default_security_groups(self, ec2_session, reservation, vpc, management_sg_id,
                                               need_management_access):

        isolated_sg = self._get_or_create_sandbox_isolated_security_group(ec2_session, management_sg_id, reservation,
                                                                          vpc, need_management_access)
        default_sg = self._get_or_create_sandbox_default_security_group(ec2_session, management_sg_id, reservation, vpc,
                                                                        isolated_sg=isolated_sg,
                                                                        need_management_access=need_management_access)

        return [isolated_sg, default_sg]

    def _get_or_create_sandbox_default_security_group(self, ec2_session, management_sg_id, reservation, vpc,
                                                      isolated_sg, need_management_access):
        sg_name = self.security_group_service.sandbox_default_sg_name(reservation.reservation_id)

        security_group = self.security_group_service.get_security_group_by_name(vpc=vpc, name=sg_name)

        if not security_group:
            security_group = \
                self.security_group_service.create_security_group(ec2_session=ec2_session,
                                                                  vpc_id=vpc.id,
                                                                  security_group_name=sg_name)

            tags = self.tag_service.get_sandbox_default_security_group_tags(name=sg_name, reservation=reservation)

            self.tag_service.set_ec2_resource_tags(security_group, tags)

            self.security_group_service.set_shared_reservation_security_group_rules(security_group=security_group,
                                                                                    management_sg_id=management_sg_id,
                                                                                    isolated_sg=isolated_sg,
                                                                                    need_management_sg=need_management_access)

        return security_group

    def _get_or_create_sandbox_isolated_security_group(self, ec2_session, management_sg_id, reservation, vpc,
                                                       need_management_access):
        sg_name = self.security_group_service.sandbox_isolated_sg_name(reservation.reservation_id)

        security_group = self.security_group_service.get_security_group_by_name(vpc=vpc, name=sg_name)

        if not security_group:
            security_group = \
                self.security_group_service.create_security_group(ec2_session=ec2_session,
                                                                  vpc_id=vpc.id,
                                                                  security_group_name=sg_name)

            tags = self.tag_service.get_sandbox_isolated_security_group_tags(name=sg_name, reservation=reservation)

            self.tag_service.set_ec2_resource_tags(security_group, tags)

            self.security_group_service.set_isolated_security_group_rules(security_group=security_group,
                                                                          management_sg_id=management_sg_id,
                                                                          need_management_access=need_management_access)

        return security_group

    def _get_or_create_vpc(self, cidr, ec2_session, reservation):
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                        reservation_id=reservation.reservation_id)
        if not vpc:
            vpc = self.vpc_service.create_vpc_for_reservation(ec2_session=ec2_session,
                                                              reservation=reservation,
                                                              cidr=cidr)
        return vpc

    def _create_prepare_create_keys_result(self, action, access_key):
        action_result = CreateKeysActionResult()
        action_result.actionId = action.actionId
        action_result.success = True
        action_result.infoMessage = 'PrepareCreateKeys finished successfully'
        action_result.accessKey = access_key

        return action_result

    def _create_prepare_network_result(self, action, security_groups, vpc):
        action_result = PrepareCloudInfraResult()
        action_result.actionId = action.actionId
        action_result.success = True
        action_result.infoMessage = 'PrepareCloudInfra finished successfully'
        action_result.vpcId = vpc.id
        action_result.securityGroupId = [sg.id for sg in security_groups]

        return action_result

    def _create_prepare_subnet_result(self, action, subnet):
        action_result = PrepareSubnetActionResult()
        action_result.actionId = action.actionId
        action_result.subnetId = subnet.subnet_id
        action_result.success = True
        action_result.infoMessage = 'PrepareSubnet finished successfully'

        return action_result

    @staticmethod
    def _create_fault_action_result(action, e):
        action_result = ActionResultBase()
        action_result.actionId = action.actionId
        action_result.success = False
        action_result.errorMessage = 'PrepareSandboxInfra ended with the error: {0}'.format(e)
        return action_result

    @retry(stop_max_attempt_number=30, wait_fixed=1000)
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

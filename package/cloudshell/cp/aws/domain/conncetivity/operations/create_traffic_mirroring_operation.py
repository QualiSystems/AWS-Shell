import itertools
import socket
from collections import defaultdict

from cloudshell.cp.aws.domain.conncetivity.operations.traffic_mirror_cleaner import TrafficMirrorCleaner
from cloudshell.cp.aws.models.traffic_mirror_fulfillment import TrafficMirrorFulfillment, CreateResult

flatten = itertools.chain.from_iterable


class CreateTrafficMirrorOperation(object):
    def __init__(self, tag_service, session_number_service):
        """
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        :param cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services.SessionNumberService session_number_service:
        """
        self._tag_service = tag_service
        self._session_number_service = session_number_service

    def create(self,
               ec2_client,
               reservation,
               actions,
               logger,
               cloudshell):
        """
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param EC2.Client ec2_client:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions: what traffic mirroring sessions,
               targets and filters to apply
        :param logger:
        :return:
        """

        # concern - cancellation context

        logger.info('Received request to deploy traffic mirroring. Here are the params:\n' + '\n'
                    .join(str(x) for x in actions))

        self._validate_actions(actions, logger)
        self._checkout_session_numbers(actions, cloudshell, logger, reservation)

        target_nics_to_fulfillments = self._convert_traffic_requests_to_fulfillments(actions, reservation)
        target_nics = target_nics_to_fulfillments.keys()
        fulfillments = list(flatten(target_nics_to_fulfillments.values()))

        try:
            self._get_or_create_targets(ec2_client, reservation, target_nics, target_nics_to_fulfillments)
            self._get_or_create_sessions(ec2_client, fulfillments)

            success = True
            message = 'Success'

        except Exception as e:
            success = False
            message = e.message
            TrafficMirrorCleaner.rollback(ec2_client, fulfillments)

        result = CreateResult(success, fulfillments, message)
        return result

    def _get_or_create_targets(self, ec2_client, reservation, target_nics, target_nics_to_fulfillments):
        targets_found_nics_to_target_id = self._find_traffic_targets_associated_with_nics(ec2_client, target_nics)
        self._create_targets_or_assign_existing_targets(ec2_client,
                                                        target_nics_to_fulfillments,
                                                        targets_found_nics_to_target_id,
                                                        self._tag_service,
                                                        reservation)

    def _get_or_create_sessions(self, ec2_client, fulfillments):
        session_name_to_fulfillment = {f.session_name: f for f in fulfillments}
        session_name_to_found_session = self._find_sessions(ec2_client, session_name_to_fulfillment.keys())
        for s in session_name_to_fulfillment.keys():
            fulfillment = session_name_to_fulfillment[s]
            if s not in session_name_to_found_session.keys():
                session = self._create_session(ec2_client, fulfillment)
                fulfillment.mirror_session_id = session['TrafficMirrorSessionId']
            else:
                found_session = session_name_to_found_session[s]
                fulfillment.mirror_session_id = found_session['TrafficMirrorSessionId']

    def _create_targets_or_assign_existing_targets(self, ec2_client,
                                                   target_nics_to_fulfillments,
                                                   nics_to_found_target_ids,
                                                   tag_service,
                                                   reservation):
        """
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        """
        for target_nic in target_nics_to_fulfillments.keys():
            if target_nic not in nics_to_found_target_ids:
                target_tags = tag_service.get_default_tags(target_nic, reservation)
                target = self._create_target_from_nic(ec2_client, target_nic, target_tags)
                self._assign_target_to_fulfillments(target_nics_to_fulfillments[target_nic], target)
            else:
                self._assign_target_to_fulfillments(target_nics_to_fulfillments[target_nic],
                                                    nics_to_found_target_ids[target_nic])

    @staticmethod
    def _convert_traffic_requests_to_fulfillments(actions, reservation):
        target_nics_to_fulfillments = defaultdict(list)
        [target_nics_to_fulfillments[x.actionParams.targetNicId].append(TrafficMirrorFulfillment(x, reservation))
         for x in actions]
        return target_nics_to_fulfillments

    @staticmethod
    def _create_target_from_nic(ec2_client, target_nic, tags):
        # todo improve error handling
        description = str(tags[0]['Value'])  # description follows the same scheme as name tag
        response = ec2_client.create_traffic_mirror_target(NetworkInterfaceId=target_nic,
                                                           Description=description,
                                                           TagSpecifications=[
                                                               {
                                                                   'ResourceType': 'traffic-mirror-target',
                                                                   'Tags': tags
                                                               }
                                                           ])
        return response['TrafficMirrorTarget']['TrafficMirrorTargetId']

    @staticmethod
    def _find_sessions(ec2_client, session_names):
        """
        :param list(str) session_names:
        """
        traffic_mirror_sessions = []
        response = ec2_client.describe_traffic_mirror_sessions(
            Filters=[
                {
                    'Name': 'description',
                    'Values': session_names
                },
            ],
            MaxResults=100)
        traffic_mirror_sessions.extend(response['TrafficMirrorSessions'])
        while 'NextToken' in response:
            response = ec2_client.describe_traffic_mirror_sessions(NextToken=response['NextToken'])
            traffic_mirror_sessions.extend(response['TrafficMirrorSessions'])
        return {t['Description']: t for t in traffic_mirror_sessions}

    @staticmethod
    def _find_traffic_targets_associated_with_nics(ec2_client, target_nics):
        response = ec2_client.describe_traffic_mirror_targets(Filters=[{
            'Name': 'network-interface-id',
            'Values': target_nics}])
        return {x['NetworkInterfaceId']: x['TrafficMirrorTargetId'] for x in response['TrafficMirrorTargets']}

    @staticmethod
    def _assign_target_to_fulfillments(fulfillments, traffic_target_id):
        for fulfillment in fulfillments:
            fulfillment.traffic_mirror_target_id = traffic_target_id

    @staticmethod
    def _create_filter(ec2_client, tags):
        description = str(tags[0]['Value'])  # description follows the same scheme as name tag
        response = ec2_client.create_traffic_mirror_filter(
            Description=description,
            TagSpecifications=[
                {
                    'ResourceType': 'traffic-mirror-filter',
                    'Tags': tags
                },
            ])

        return response

    def _create_session(self, ec2_client, fulfillment):
        """
        :param cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment fulfillment:
        """
        response = self._create_filter(ec2_client,
                                       self._tag_service.get_default_tags('filter-' + fulfillment.session_name,
                                                                          fulfillment.reservation))

        fulfillment.traffic_mirror_filter_id = response['TrafficMirrorFilter']['TrafficMirrorFilterId']

        self._create_filter_rules(ec2_client, fulfillment)

        response = ec2_client.create_traffic_mirror_session(
            NetworkInterfaceId=fulfillment.source_nic_id,
            TrafficMirrorTargetId=fulfillment.traffic_mirror_target_id,
            TrafficMirrorFilterId=fulfillment.traffic_mirror_filter_id,
            SessionNumber=int(fulfillment.session_number),
            Description=fulfillment.session_name,
            TagSpecifications=[
                {
                    'ResourceType': 'traffic-mirror-session',
                    'Tags': self._tag_service.get_default_tags('session-' + fulfillment.session_name,
                                                               fulfillment.reservation)
                }
            ]
        )
        return response['TrafficMirrorSession']

    def _validate_actions(self, actions, logger):
        self._session_numbers_are_valid(actions, logger)  # must be 1-32766 or NONE

    def _checkout_session_numbers(self, actions, cloudshell, logger, reservation):
        """
        session number must be between 1-32766 and unique per source nic id;
        every traffic mirror session must have a number assigned
        the number represents the priority of a target when pulling the traffic packets.

        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions:
        """

        source_nic_to_traffic_action = defaultdict(list)
        [source_nic_to_traffic_action[a.actionParams.sourceNicId].append(a) for a in actions]
        for source in source_nic_to_traffic_action.keys():
            self.get_unique_session_number_and_assign_to_mirror_session_request(cloudshell, logger, reservation, source,
                                                                                source_nic_to_traffic_action)

    def get_unique_session_number_and_assign_to_mirror_session_request(self, cloudshell, logger, reservation, source,
                                                                       source_nic_to_traffic_action):
        for action in source_nic_to_traffic_action[source]:
            session_number = action.actionParams.sessionNumber
            action.actionParams.sessionNumber = self._session_number_service.checkout(cloudshell,
                                                                                      logger,
                                                                                      reservation,
                                                                                      source,
                                                                                      session_number)

    @staticmethod
    def _session_numbers_are_valid(actions, logger):
        """
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions:
        :param logging.Logger logger:
        """
        error_msg = 'Session number must be either empty or an integer in the range 1-32766'

        # must be 1-32766 or NONE
        for a in actions:
            try:
                session_number = int(a.actionParams.sessionNumber)
                if session_number and \
                        not isinstance(session_number, (int, long)) \
                        or session_number > 32766 \
                        or session_number < 1:
                    logger.error(error_msg + '\nSession number is {0}'.format(session_number))
                    raise Exception(error_msg)
            except ValueError:
                a.actionParams.sessionNumber = None

    def _create_filter_rules(self, ec2_client, fulfillment):
        """
        creates filter rules requested for a particular session
        :param cloudshell.cp.aws.models.traffic_mirror_fulfillment.TrafficMirrorFulfillment fulfillment:
        """
        i = 0
        for rule in fulfillment.filter_rules:
            i += 1
            description = 'filter_rule_{0}_{1}'.format(i, fulfillment.traffic_mirror_filter_id)
            kwargs = {
                'TrafficMirrorFilterId': fulfillment.traffic_mirror_filter_id,
                'RuleAction': 'accept',
                'Description': description
            }

            if rule.sourcePortRange:
                kwargs['SourcePortRange'] = rule.sourcePortRange

            if rule.destinationPortRange:
                kwargs['DestinationPortRange'] = rule.destinationPortRange

            kwargs['TrafficDirection'] = rule.direction
            kwargs['RuleNumber'] = i
            kwargs['Protocol'] = rule.protocol if isinstance(rule.protocol, int) else socket.getprotobyname(
                rule.protocol)
            kwargs['DestinationCidrBlock'] = rule.destinationCidr or self._get_destination_cidr()
            kwargs['SourceCidrBlock'] = rule.sourceCidr or self._get_source_cidr()

            ec2_client.create_traffic_mirror_filter_rule(**kwargs)

    @staticmethod
    def _get_source_cidr():
        return '0.0.0.0/0'

    @staticmethod
    def _get_destination_cidr():
        return '0.0.0.0/0'

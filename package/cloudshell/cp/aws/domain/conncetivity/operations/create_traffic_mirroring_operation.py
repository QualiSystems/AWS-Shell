from collections import defaultdict
import socket
import itertools

from jsonpickle import json

flatten = itertools.chain.from_iterable


class CreateTrafficMirroringOperation(object):
    def __init__(self, tag_service, session_number_service):
        """
        :param cloudshell.cp.aws.domain.services.ec2.tags.TagService tag_service:
        :param cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation.SessionNumberService session_number_service:
        """
        self._tag_service = tag_service
        self._session_number_service = session_number_service

    def create(self,
               ec2_client,
               ec2_session,
               s3_session,
               reservation,
               aws_ec2_datamodel,
               actions,
               cancellation_context,
               logger,
               cloudshell):
        """
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param EC2.Client ec2_client:
        :param ec2_session:
        :param s3_session:
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param aws_ec2_datamodel:
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions: what traffic mirroring sessions,
               targets and filters to apply
        :param cancellation_context:
        :param logger:
        :return:
        """

        # concern - cancellation context & rollback

        logger.info('Received request to deploy traffic mirroring. Here are the params:\n' + '\n'
                    .join(str(x) for x in actions))

        self._validate_actions(actions, logger)
        self._checkout_session_numbers(actions, cloudshell, logger, reservation)

        target_nics_to_fulfillments = self._convert_traffic_requests_to_fulfillments(actions, reservation)
        target_nics = target_nics_to_fulfillments.keys()
        fulfillments = flatten(target_nics_to_fulfillments.values())

        # targets
        # concern - try to create a target for a nic which is already associated as a target!
        self._get_or_create_targets(ec2_client, reservation, target_nics, target_nics_to_fulfillments)

        # concern - try to associate a source / target to a session, when already associated
        # sessions
        self._get_or_create_sessions(ec2_client, fulfillments)  # self._create_filter(ec2_client, default_tags)

        result = CreateResult(False)
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
        [target_nics_to_fulfillments[x.actionParams.targetNicId].append(TrafficMirroringFulfillment(x, reservation))
         for x in actions]
        return target_nics_to_fulfillments

    @staticmethod
    def _create_target_from_nic(ec2_client, target_nic, tags):
        # todo improve error handling
        description = str(tags[0])  # description follows the same scheme as name tag
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
        # todo we want to get traffic mirror sessions based on the naming scheme

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
        """ response describes existing traffic mirror targets that have the target nics
        we want to use those nics instead of creating them

        <DescribeTrafficMirrorTargetsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
            <requestId>51c75cfa-c517-4478-8a20-c5c53d719875</requestId>
            <trafficMirrorTargetSet>
                <item>
                    <networkInterfaceId>eni-0fedfb8d7795f2713</networkInterfaceId>
                    <ownerId>851646629437</ownerId>
                    <tagSet/>
                    <trafficMirrorTargetId>tmt-0e6d57a5bf7f1a4d4</trafficMirrorTargetId>
                    <type>network-interface</type>
                </item>
            </trafficMirrorTargetSet>
        </DescribeTrafficMirrorTargetsResponse>
        """
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
        # todo determine a scheme for mirror descriptions
        description = str(tags[0])   # description follows the same scheme as name tag
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
        :param TrafficMirroringFulfillment fulfillment:
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
        :param TrafficMirroringFulfillment fulfillment:
        """
        i = 0
        for rule in fulfillment.filter_rules:
            i+=1
            description = 'filter_rule_{0}_{1}'.format(i, fulfillment.traffic_mirror_filter_id)
            kwargs={
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
            kwargs['Protocol'] = rule.protocol if isinstance(rule.protocol, int) else socket.getprotobyname(rule.protocol)
            kwargs['DestinationCidrBlock'] = rule.destinationCidr or self._get_destination_cidr()
            kwargs['SourceCidrBlock'] = rule.sourceCidr or self._get_source_cidr()

            ec2_client.create_traffic_mirror_filter_rule(**kwargs)

    def _get_source_cidr(self):
        return '0.0.0.0/0'

    def _get_destination_cidr(self):
        return '0.0.0.0/0'


class CreateResult(object):
    def __init__(self, success):
        self.Success = success


class TrafficMirroringFulfillment(object):
    def __init__(self, action, reservation):
        """
        :param cloudshell.cp.core.models.CreateTrafficMirroring action:
        :return:
        """
        self.reservation = reservation
        self.traffic_mirror_filter_id = None
        self.action_id = action.actionId
        self.target_nic_id = action.actionParams.targetNicId
        self.traffic_mirror_target_id = None
        self.source_nic_id = action.actionParams.sourceNicId
        self.session_number = action.actionParams.sessionNumber  # todo handle empty session number, get next available, etc
        self.session_name = self._get_mirror_session_name()
        self.mirror_session_id = None
        self.filter_rules = action.actionParams.filterRules

    def _get_mirror_session_name(self):
        """
        :param TrafficMirroringFulfillment fulfillment:
        :return:
        """
        return '{2}_{0}_{1}'.format(self.source_nic_id, self.target_nic_id, self.session_number)


class SessionNumberService(object):
    def checkout(self, cloudshell, logger, reservation, source_nic, specific_number=None):
        """
        :param cloudshell.cp.aws.models.reservation_model.ReservationModel reservation:
        :param logging.Logger logger:
        :param cloudshell.api.cloudshell_api.CloudShellAPISession cloudshell:
        :param str source_nic:
        :param str specific_number:
        :return:
        """
        selection_criteria = self._get_selection_criteria(source_nic, reservation.reservation_id, specific_number)

        try:
            result = cloudshell.CheckoutFromPool(selection_criteria)
            return result.Items[0]
        except Exception as e:
            logger.error(unavailable_msg(source_nic, reservation.reservation_id))
            logger.error(e.message)
            raise Exception(unavailable_msg(source_nic, reservation.reservation_id))

    def release(self, source_nic, specific_number=None):
        pass

    @staticmethod
    def _get_selection_criteria(source_nic, reservation_id, specific_number=None):
        request = {
            'isolation': 'Exclusive',
            'reservationId': reservation_id,
            'poolId': source_nic,  # The session number determines the order that traffic mirror sessions are evaluated when an interface is used by multiple sessions that have the same interface, but have different traffic mirror targets and traffic mirror filters. Traffic is only mirrored one time.
            'ownerId': 'admin'
        }

        if not specific_number:
            request['type'] = 'NextAvailableNumericFromRange'
            request['requestedRange'] = {'Start': 1, 'End': 32766}
        else:
            request['type'] = 'SpecificNumeric'
            request['requestedItem'] = {'Value': specific_number}

        selection_criteria = json.dumps(request)
        return selection_criteria


UNAVAILABLE_MSG = 'Was not able to find an available session number for {0}.\n' \
                  'Please note that session number must be between 1-32766 and unique for a particular source NIC.\n' \
                  'To learn more, please see documentation at ' \
                  'https://docs.aws.amazon.com/vpc/latest/mirroring/traffic-mirroring-session.html' \
                  '\nPlease also check logs at %PROGRAMDATA%\\QualiSystems\\logs\\{1} for additional information.'


def unavailable_msg(source_nic, reservation_id):
    return UNAVAILABLE_MSG.format(source_nic, reservation_id)

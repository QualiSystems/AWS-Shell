from collections import defaultdict
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

        logger.info('Received request to deploy traffic mirroring. Here are the params:\n' + '\n'
                    .join(str(x) for x in actions))

        # for each action, provide a target, a filter and a session
        # get or create; but I want to take advantage of bulk

        # order: 1. targets, 2. filters 3. rules 4. sessions

        # validations
        self._validate_actions(actions)
        self._checkout_session_numbers(actions, cloudshell, logger, reservation)

        # targets
        target_nics_to_fulfillments = self._convert_traffic_requests_to_fulfillments(actions, reservation)
        target_nics = target_nics_to_fulfillments.keys()
        targets_found_nics_to_target_id = self._find_traffic_targets_associated_with_nics(ec2_client, target_nics)
        # self._get_or_create_targets(ec2_client,
        #                             target_nics_to_fulfillments,
        #                             targets_found_nics_to_target_id,
        #                             self._tag_service,
        #                             reservation)

        # sessions
        fulfillments = flatten(target_nics_to_fulfillments.values())
        session_name_to_fulfillment = {f.session_name: f for f in fulfillments}
        session_name_to_found_session = self._find_sessions(ec2_client, session_name_to_fulfillment.keys())

        for s in session_name_to_fulfillment.keys():
            fulfillment = session_name_to_fulfillment[s]
            if s not in session_name_to_found_session.keys():
                session = self._create_session(ec2_client, fulfillment)
                # assign session to fulfillment
            else:
                found_session = session_name_to_found_session[s]
                fulfillment.mirror_session_id = found_session['TrafficMirrorSessionId']

        # assign found sessions to fulfilmments - create session will be handled later, along with filters and rules

        # self._create_filter(ec2_client, default_tags)

        # create or get rules, or invalidate request

        # create or get filter, or invalidate request

        # create or get session, or invalidate request

        result = CreateResult(False)
        return result

    def _get_or_create_targets(self, ec2_client,
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
        description = str(tags[0])  # description follows the same scheme as name tag
        response = ec2_client.create_traffic_mirror_target(NetworkInterfaceId=target_nic,
                                                           Description=description,
                                                           TagSpecifications=[
                                                               {
                                                                   'ResourceType': 'traffic-mirror-target',
                                                                   'Tags': tags
                                                               }
                                                           ])
        """ response -
            {
                'TrafficMirrorTarget': {
                    'TrafficMirrorTargetId': 'string',
                    'NetworkInterfaceId': 'string',
                    'NetworkLoadBalancerArn': 'string',
                    'Type': 'network-interface',
                    'Description': 'string',
                    'OwnerId': 'string',
                    'Tags': [
                        {
                            'Key': 'string',
                            'Value': 'string'
                        },
                    ]
                },
                'ClientToken': 'string'
            }
            """
        return response

    @staticmethod
    def _find_sessions(ec2_client, session_names):
        """
        :param list(str) session_names:
        """
        # todo we want to get traffic mirror sessions based on the naming scheme

        # expected response
        """
        {'TrafficMirrorSessions': [{
                                    'Description': 'eni-0fedfb8d7795f2713_eni-0fedfb8d7795f2713',
                                    'Tags': [{'Value': 'eni-0fedfb8d7795f2713_eni-0fedfb8d7795f2713',  'Key': 'Name'}],
                                    'NetworkInterfaceId': 'eni-0fedfb8d7795f2713',
                                    'TrafficMirrorTargetId': 'tmt-09d168e2bbc92cfe6',
                                    'SessionNumber': 1,
                                    'OwnerId': '851646629437',
                                    'TrafficMirrorFilterId': 'tmf-0e6d65039d92a6aa1',
                                    'TrafficMirrorSessionId': 'tms-0d079edf9ab1e3fde',
                                    'VirtualNetworkId': 2120640}],
         'ResponseMetadata': {'RetryAttempts': 0,
         'HTTPStatusCode': 200,
         'RequestId': 'd18dcaa3-0bb9-41ba-93fe-aaf9289195c0',
         'HTTPHeaders': {'transfer-encoding': 'chunked',
         'content-type': 'text/xml;charset=UTF-8',
         'vary': 'accept-encoding',
         'date': 'Wed,
         25 Sep 2019 11:26:06 GMT',
         'server': 'AmazonEC2'}}}
        """
        traffic_mirror_sessions = []
        response = ec2_client.describe_traffic_mirror_sessions(
            Filters=[
                {
                    'Name': 'Name',
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
        description = 'string'
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
        """
        response = client.create_traffic_mirror_session(
        NetworkInterfaceId='string',
        TrafficMirrorTargetId='string',
        TrafficMirrorFilterId='string',
        PacketLength=123,
        SessionNumber=123,
        VirtualNetworkId=123,
        Description='string',
        TagSpecifications=[
            {
                'ResourceType': 'client-vpn-endpoint'|'customer-gateway'|'dedicated-host'|'dhcp-options'|'elastic-ip'|'fleet'|'fpga-image'|'host-reservation'|'image'|'instance'|'internet-gateway'|'launch-template'|'natgateway'|'network-acl'|'network-interface'|'reserved-instances'|'route-table'|'security-group'|'snapshot'|'spot-instances-request'|'subnet'|'traffic-mirror-filter'|'traffic-mirror-session'|'traffic-mirror-target'|'transit-gateway'|'transit-gateway-attachment'|'transit-gateway-route-table'|'volume'|'vpc'|'vpc-peering-connection'|'vpn-connection'|'vpn-gateway',
                'Tags': [
                    {
                        'Key': 'string',
                        'Value': 'string'
                    },
                ]
            },
        ],
        DryRun=True|False,
        ClientToken='string'
        )
        """

        # create filter
        # create session number, safely
        # session number is the priority sessions from the same source interface are handled
        # therefore session number must be unique per source nic?

        ec2_client.create_traffic_mirror_session(
            NetworkInterfaceId=fulfillment.source_nic_id,
            TrafficMirrorTargetId=fulfillment.traffic_mirror_target_id,
            TrafficMirrorFilterId=fulfillment.traffic_mirror_filter_id,
            SessionNumber=fulfillment.session_number,
            Description=fulfillment.session_name,
            TagSpecifications=[
                {
                    'ResourceType': 'traffic-mirror-session',
                    'Tags': self._tag_service.get_default_tags(fulfillment.session_name,
                                                               fulfillment.reservation)
                }
            ]
        )

    def _validate_actions(self, actions):
        self._session_numbers_are_valid(actions)  # must be 1-32766 or NONE

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
            # todo assign session number to action params; make sure empty string is treated as none
            [self._session_number_service.checkout(
                cloudshell=cloudshell,
                logger=logger,
                reservation=reservation,
                source_nic=source,
                specific_number=action.actionParams.sessionNumber)
             for action in source_nic_to_traffic_action[source]]
        pass

    def _session_numbers_are_valid(self, actions):
        """
        :param list[cloudshell.cp.core.models.CreateTrafficMirroring] actions:
        """
        error_msg = 'Session number must be either empty or an integer in the range 1-32766'

        # must be 1-32766 or NONE
        for a in actions:
            session_number = a.actionParams.sessionNumber
            if session_number == '':
                a.actionParams.sessionNumber = None
            if session_number and not int(session_number)==session_number:
                raise Exception(error_msg)
            if session_number and (session_number > 32766 or session_number < 1):
                raise Exception(error_msg)



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
        :param int specific_number:
        :return:
        """
        selection_criteria = self._get_selection_criteria(source_nic, reservation.reservation_id, specific_number)

        try:
            result = cloudshell.CheckoutFromPool(selection_criteria)
            return result
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
            'reservation_id': reservation_id,
            'pool_id': source_nic,
            'owner_id': 'admin'
        }

        if not specific_number:
            request['type'] = 'NextAvailableNumericFromRange'
            request['requestedRange'] = {'Start': 1, 'End': 32766}
        else:
            request['type'] = 'SelectSpecificNumericRequest',
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

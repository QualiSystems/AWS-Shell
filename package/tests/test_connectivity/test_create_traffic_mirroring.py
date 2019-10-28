import logging
from unittest import TestCase
from uuid import uuid4

import boto3
from cloudshell.api.cloudshell_api import CloudShellAPISession

from mock import Mock

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService

from cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation import \
    CreateTrafficMirrorOperation
from cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services import SessionNumberService
from cloudshell.cp.aws.domain.services.ec2.mirroring import TrafficMirrorService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.reservation_model import ReservationModel
from cloudshell.cp.core import DriverRequestParser
from cloudshell.cp.core.models import CreateTrafficMirroring, CreateTrafficMirroringParams


class TestCreateTrafficMirroring(TestCase):
    # def setUp(self):
    #     self.ec2_client = boto3.client('ec2')
    #     try:
    #         self.cloudshell = CloudShellAPISession(host='localhost',
    #                                                username='admin',
    #                                                password='admin',
    #                                                domain='Global')
    #     except:
    #         raise Exception('failed to connect to Quali Server')
    #     # self.res = self.cloudshell.CreateImmediateReservation('test', 'admin', 120).Reservation
    #     # reservation = self.cloudshell.CreateImmediateTopologyReservation('trafficMirrorTest', 'admin', 120,
    #     #                                                    topologyFullPath='AWS-eu-west-1')
    #     # while True:
    #     #     self.res = self.cloudshell.GetReservationDetails(reservation.Reservation.Id).ReservationDescription
    #     #     if self.res.ProvisioningStatus.lower() == 'active':
    #     #         break
    #     #     time.sleep(10)
    #
    #     self.res = self.cloudshell.GetReservationDetails('b9818bde-fc86-49f2-beae-74e238a3ad07').ReservationDescription
    #
    # def tearDown(self):
    #     # self.cloudshell.EndReservation(self.res.Id)
    #     # TrafficMirrorCleaner.rollback(self.ec2_client, self.fulfillments)
    #     pass
    #
    # def test_create_traffic_mirroring(self):
    #     tag_service = TagService(Mock())
    #     session_number_service = SessionNumberService()
    #     traffic_mirror_service = TrafficMirrorService()
    #     cancellation_service = CommandCancellationService()
    #     op = CreateTrafficMirrorOperation(tag_service,
    #                                       session_number_service,
    #                                       traffic_mirror_service,
    #                                       cancellation_service)
    #
    #     reservation_context = Mock()
    #     reservation_context.reservation_id = self.res.Id
    #     reservation = ReservationModel(reservation_context)
    #     reservation.blueprint = 'lalala'
    #     reservation.owner = 'admin'
    #     reservation.domain = 'global'
    #
    #     source_nic = next(next(p.Value for p in r.VmDetails.NetworkData[0].AdditionalData if p.Name=='nic') for r in self.res.Resources if 'Source' in r.Name)
    #     target_nic = next(next(p.Value for p in r.VmDetails.NetworkData[0].AdditionalData if p.Name=='nic') for r in self.res.Resources if 'Target' in r.Name)
    #
    #     request = '''
    #     {
    #         "driverRequest": {
    #                             "actions": [
    #                                             {
    #                                                 "actionId": "a156d3db-78fe-4c19-9039-a225d0360119",
    #                                                 "actionTarget": null,
    #                                                 "type": "CreateTrafficMirroring",
    #                                                 "actionParams": {"type": "CreateTrafficMirroringParams",
    #                                                                  "sourceNicId": "eni-0bf9b403bd8d36a79",
    #                                                                  "targetNicId": "eni-060613fdccd935b67",
    #                                                                  "sessionNumber": "116",
    #                                                                  "filterRules": [
    #                                                                     {
    #                                                                         "type": "TrafficFilterRule",
    #                                                                         "direction": "ingress",
    #                                                                         "sourcePortRange": {
    #                                                                             "type": "PortRange",
    #                                                                             "fromPort": "123",
    #                                                                             "toPort": "123"
    #                                                                         },
    #                                                                         "protocol": "udp"
    #                                                                     }
    #                                                                  ]
    #                                                                  }
    #                                             }
    #                                         ]
    #                           }
    #     }
    #     '''
    #
    #     request_parser = DriverRequestParser()
    #     actions = request_parser.convert_driver_request_to_actions(request)
    #     logger = Mock()
    #     actions[0].actionParams.sourceNicId = source_nic
    #     actions[0].actionParams.targetNicId = target_nic
    #
    #     logging.disable(logging.DEBUG)
    #
    #     cancellation_context = Mock()
    #     cancellation_context.is_cancelled = False
    #
    #     results = op.create(
    #         ec2_client=self.ec2_client,
    #         reservation=reservation,
    #         actions=actions,
    #         cancellation_context=cancellation_context,
    #         logger=logger,
    #         cloudshell=self.cloudshell)
    # #
    #     self.assertTrue(next(r.success for r in results)==True,
    #                     'Was not able to create traffic mirroring')

    def test_valid_create_returns_success_actions(self):
        tag_service = TagService(Mock())
        session_number_service = SessionNumberService()
        traffic_mirror_service = TrafficMirrorService()
        cancellation_service = CommandCancellationService()
        reservation_context = Mock()
        reservation_context.reservation_id = str(uuid4())
        reservation = ReservationModel(reservation_context)
        reservation.blueprint = 'lalala'
        reservation.owner = 'admin'
        reservation.domain = 'global'
        describe_mirror_targets_result = {
            'TrafficMirrorTargets': [
                {
                    'NetworkInterfaceId': 'bbbb',
                    'TrafficMirrorTargetId': 'cccc'
                }
            ]
        }

        create_traffic_mirror_target_result = {
            'TrafficMirrorTarget': {
                'TrafficMirrorTargetId': 'tmt-5050'
            }
        }

        create_filter_result = {
            'TrafficMirrorFilter': {
                'TrafficMirrorFilterId': 'tmf-5050'
            }
        }

        create_traffic_mirror_session_result = {
            'TrafficMirrorSession': {
                'TrafficMirrorSessionId': 'tms-5050'
            }
        }

        ec2_client = Mock()
        ec2_client.describe_traffic_mirror_targets = Mock(return_value=describe_mirror_targets_result)
        ec2_client.create_traffic_mirror_target = Mock(return_value=create_traffic_mirror_target_result)
        ec2_client.create_traffic_mirror_filter = Mock(return_value=create_filter_result)
        ec2_client.create_traffic_mirror_session = Mock(return_value=create_traffic_mirror_session_result)

        cancellation_context = Mock()
        cancellation_context.is_cancelled = False
        logger = Mock()
        cloudshell = Mock()
        checkout_result = Mock()
        checkout_result.Items = [5]
        cloudshell.CheckoutFromPool = Mock(return_value=checkout_result)

        action = CreateTrafficMirroring()
        action.actionId = str(uuid4())
        action.actionParams = CreateTrafficMirroringParams()
        action.actionParams.sessionNumber = '5'
        action.actionParams.sourceNicId = 'a'
        action.actionParams.targetNicId = 'b'
        actions = [action]

        op = CreateTrafficMirrorOperation(tag_service,
                                          session_number_service,
                                          traffic_mirror_service,
                                          cancellation_service)

        results = op.create(ec2_client=ec2_client,
                            reservation=reservation,
                            actions=actions,
                            cancellation_context=cancellation_context,
                            logger=logger,
                            cloudshell=cloudshell)

        self.assertTrue([x for x in results if x.success])

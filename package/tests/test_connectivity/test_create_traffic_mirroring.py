import json
import logging
from unittest import TestCase
from uuid import uuid4

import boto3
from cloudshell.api.cloudshell_api import CloudShellAPISession
from jsonschema import validate

from mock import Mock

from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService

from cloudshell.cp.aws.domain.conncetivity.operations.traffic_mirroring_operation import \
    TrafficMirrorOperation, CREATE_SCHEMA, REMOVE_SCHEMA
from cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services import SessionNumberService
from cloudshell.cp.aws.domain.services.ec2.mirroring import TrafficMirrorService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.reservation_model import ReservationModel
from cloudshell.cp.core import DriverRequestParser
from cloudshell.cp.core.models import CreateTrafficMirroring, CreateTrafficMirroringParams


class TestCreateTrafficMirroring(TestCase):
    # def test_create_traffic_mirroring(self):
    #     reservation_id = '98900220-1216-4d81-8481-a1356093adac'
    #     session_number = ''
    #
    #     # region prep
    #     self.ec2_client = boto3.client('ec2')
    #     try:
    #         self.cloudshell = CloudShellAPISession(host='localhost',
    #                                                username='admin',
    #                                                password='admin',
    #                                                domain='Global')
    #     except:
    #         raise Exception('failed to connect to Quali Server')
    #
    #     self.res = self.cloudshell.GetReservationDetails(reservation_id).ReservationDescription
    #
    #     tag_service = TagService(Mock())
    #     session_number_service = SessionNumberService()
    #     traffic_mirror_service = TrafficMirrorService()
    #     cancellation_service = CommandCancellationService()
    #     op = TrafficMirrorOperation(tag_service,
    #                                 session_number_service,
    #                                 traffic_mirror_service,
    #                                 cancellation_service)
    #
    #     reservation_context = Mock()
    #     reservation_context.reservation_id = self.res.Id
    #     reservation = ReservationModel(reservation_context)
    #     reservation.blueprint = 'lalala'
    #     reservation.owner = 'admin'
    #     reservation.domain = 'global'
    #
    #     source_nic = next(next(p.Value for p in r.VmDetails.NetworkData[0].AdditionalData if p.Name == 'nic') for r in
    #                       self.res.Resources if 'Source' in r.Name)
    #     target_nic = next(next(p.Value for p in r.VmDetails.NetworkData[0].AdditionalData if p.Name == 'nic') for r in
    #                       self.res.Resources if 'Target' in r.Name)
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
    #                                                                  "sessionNumber": "",
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
    #     actions[0].actionParams.sessionNumber = session_number
    #
    #     logging.disable(logging.DEBUG)
    #
    #     cancellation_context = Mock()
    #     cancellation_context.is_cancelled = False
    #
    #     # endregion
    #
    #     results = op.create(
    #         ec2_client=self.ec2_client,
    #         reservation=reservation,
    #         actions=actions,
    #         cancellation_context=cancellation_context,
    #         logger=logger,
    #         cloudshell=self.cloudshell)
    #     #
    #     self.assertTrue(next(r.success for r in results) == True,
    #                     'Was not able to create traffic mirroring')
    #
    # def test_remove_traffic_mirroring(self):
    #     reservation_id = '97fb8c3a-0eaa-4340-94db-86dc4c3ed897'
    #     session_id = "tms-07eaf6f71e8bfa0e1"
    #     target_nic_id = "eni-0048855a9867bdc43"
    #
    #     # region prep
    #     self.ec2_client = boto3.client('ec2')
    #     try:
    #         self.cloudshell = CloudShellAPISession(host='localhost',
    #                                                username='admin',
    #                                                password='admin',
    #                                                domain='Global')
    #     except:
    #         raise Exception('failed to connect to Quali Server')
    #
    #     self.res = self.cloudshell.GetReservationDetails(reservation_id).ReservationDescription
    #
    #     tag_service = TagService(Mock())
    #     session_number_service = SessionNumberService()
    #     traffic_mirror_service = TrafficMirrorService()
    #     cancellation_service = CommandCancellationService()
    #     op = TrafficMirrorOperation(tag_service,
    #                                 session_number_service,
    #                                 traffic_mirror_service,
    #                                 cancellation_service)
    #
    #     reservation_context = Mock()
    #     reservation_context.reservation_id = self.res.Id
    #     reservation = ReservationModel(reservation_context)
    #     reservation.blueprint = 'lalala'
    #     reservation.owner = 'admin'
    #     reservation.domain = 'global'
    #
    #     request = '''
    #     {
    #         "driverRequest": {
    #                             "actions": [
    #                                             {
    #                                                 "actionId": "a156d3db-78fe-4c19-9039-a225d0360119",
    #                                                 "type": "RemoveTrafficMirroring",
    #                                                 "sessionId": "tms-0f457d0854e043637",
    #                                                 "targetNicId": "eni-0048855a9867bdc43"
    #                                             }
    #                                         ]
    #                           }
    #     }
    #     '''
    #
    #     request_parser = DriverRequestParser()
    #     actions = request_parser.convert_driver_request_to_actions(request)
    #     actions[0].sessionId = session_id
    #     actions[0].targetNicId = target_nic_id
    #     logger = Mock()
    #
    #     logging.disable(logging.DEBUG)
    #
    #     cancellation_context = Mock()
    #     cancellation_context.is_cancelled = False
    #
    #     schema = {
    #         "$id": "https://example.com/geographical-location.schema.json",
    #         "$schema": "http://json-schema.org/draft-07/schema#",
    #         "title": "RemoveTrafficMirroringDriverRequest",
    #         "properties": {
    #             "actions": {
    #                 "type": "array",
    #                 "items": {"$ref": "#/definitions/remove_traffic_mirroring_request"}
    #             }
    #         },
    #         "definitions": {
    #             "remove_traffic_mirroring_request": {
    #                 "required": ["type", "actionId", "sessionId", "targetNicId"],
    #                 "properties": {
    #                     "type": {
    #                         "type": "string"
    #                     },
    #                     "actionId": {
    #                         "type": "string",
    #                     },
    #                     "sessionId": {
    #                         "type": "string",
    #                     },
    #                     "targetNicId": {
    #                         "type": "string",
    #                     }
    #                 }
    #             }
    #         }
    #
    #     }
    #
    #     validate(request, schema)
    #
    #     # endregion
    #
    #     results = op.remove(
    #         ec2_client=self.ec2_client,
    #         reservation=reservation,
    #         actions=actions,
    #         logger=logger,
    #         cloudshell=self.cloudshell)
    #     #
    #     self.assertTrue(next(r.success for r in results) == True,
    #                     'Was not able to remove traffic mirroring')

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

        op = TrafficMirrorOperation(tag_service,
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

    def test_json_validate(self):

        request = '''
        {
            "driverRequest": {
                                "actions": [
                                                {
                                                    "actionId": "a156d3db-78fe-4c19-9039-a225d0360119",
                                                    "type": "RemoveTrafficMirroring",
                                                    "sessionId": "tms-020e45731259d882d",
                                                    "targetNicId": ""
                                                }
                                            ]
                              }
        }
        '''

        result = json.loads(request)
        for a in result["driverRequest"]["actions"]:
            validate(a, REMOVE_SCHEMA)

        create_request = '''
        {
            "driverRequest": {
                                "actions": [
                                                {
                                                    "actionId": "a156d3db-78fe-4c19-9039-a225d0360119",
                                                    "type": "CreateTrafficMirroring",
                                                    "actionParams": {"type": "CreateTrafficMirroringParams",
                                                                     "sourceNicId": "eni-0bf9b403bd8d36a79",
                                                                     "targetNicId": "eni-060613fdccd935b67",
                                                                     "sessionNumber": "",
                                                                     "filterRules": [
                                                                        {
                                                                            "type": "TrafficFilterRule",
                                                                            "direction": "ingress",
                                                                            "sourcePortRange": {
                                                                                "type": "PortRange",
                                                                                "fromPort": "123",
                                                                                "toPort": "123"
                                                                            },
                                                                            "protocol": "udp"
                                                                        }
                                                                     ]
                                                                     }
                                                }
                                            ]
                              }
        }
        '''

        create_actions2 = json.loads(create_request)
        for a in create_actions2['driverRequest']['actions']:
            validate(a, CREATE_SCHEMA)


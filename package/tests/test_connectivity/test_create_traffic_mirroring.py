from unittest import TestCase
from uuid import uuid4

import boto3
from cloudshell.api.cloudshell_api import CloudShellAPISession
from mock import Mock
import logging
from cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation import \
    CreateTrafficMirrorOperation
from cloudshell.cp.aws.domain.conncetivity.operations.traffic_mirror_cleaner import TrafficMirrorCleaner
from cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services import SessionNumberService
from cloudshell.cp.aws.domain.services.ec2.mirroring import TrafficMirrorService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.reservation_model import ReservationModel
from cloudshell.cp.core import DriverRequestParser


class TestCreateTrafficMirroring(TestCase):
    def setUp(self):
        self.ec2_client = boto3.client('ec2')
        try:
            self.cloudshell = CloudShellAPISession(host='localhost',
                                                   username='admin',
                                                   password='admin',
                                                   domain='Global')
        except:
            raise Exception('failed to connect to Quali Server')
        # self.res = self.cloudshell.CreateImmediateReservation('test', 'admin', 120).Reservation
        self.res = self.cloudshell.GetReservationDetails('f1bae3a6-157f-42f8-a58e-359f8f91b1e3').ReservationDescription
        self.fulfillments = []

    def tearDown(self):
        # self.cloudshell.EndReservation(self.res.Id)
        # TrafficMirrorCleaner.rollback(self.ec2_client, self.fulfillments)
        pass

    def test_create_traffic_mirroring(self):
        tag_service = TagService(Mock())
        session_number_service = SessionNumberService()
        traffic_mirror_service = TrafficMirrorService()
        op = CreateTrafficMirrorOperation(tag_service, session_number_service, traffic_mirror_service)

        reservation_context = Mock()
        reservation_context.reservation_id = self.res.Id
        reservation = ReservationModel(reservation_context)
        reservation.blueprint = 'lalala'
        reservation.owner = 'admin'
        reservation.domain = 'global'

        request = '''
        {
            "driverRequest": {
                                "actions": [
                                                {
                                                    "actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356",
                                                    "actionTarget": null,
                                                    "type": "CreateTrafficMirroring",
                                                    "actionParams": {"type": "CreateTrafficMirroringParams",
                                                                     "sourceNicId": "eni-079bf02e7497ccad7",
                                                                     "targetNicId": "eni-0d364399642ce6c0c",
                                                                     "sessionNumber": "",
                                                                     "filterRules": []
                                                                     }
                                                }
                                            ]
                              }
        }
        '''

        request_parser = DriverRequestParser()
        actions = request_parser.convert_driver_request_to_actions(request)
        logger = Mock()
        logging.disable(logging.DEBUG)

        # todo put cancellation back in, handle rollback

        result = op.create(
            ec2_client=self.ec2_client,
            reservation=reservation,
            actions=actions,
            cancellation_context=Mock(),
            logger=logger,
            cloudshell=self.cloudshell)

        self.assertTrue(result.Success, 'Was not able to create traffic mirroring')
        self.fulfillments = result.Fulfillments

    def test_manual_tests(self):
        res = self.cloudshell.GetResourceDetails('AWS_APP i-02181554cd72946cf')
        print res

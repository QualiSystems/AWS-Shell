import logging
from unittest import TestCase

import boto3
from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
from mock import Mock

from cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation import \
    CreateTrafficMirrorOperation
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
        self.res = self.cloudshell.GetReservationDetails('f31aa724-d4e3-49bf-ac8c-405622166e1d').ReservationDescription
        self.fulfillments = []

    def tearDown(self):
        # self.cloudshell.EndReservation(self.res.Id)
        # TrafficMirrorCleaner.rollback(self.ec2_client, self.fulfillments)
        pass

    def test_create_traffic_mirroring(self):
        tag_service = TagService(Mock())
        session_number_service = SessionNumberService()
        traffic_mirror_service = TrafficMirrorService()
        cancellation_service = CommandCancellationService()
        op = CreateTrafficMirrorOperation(tag_service,
                                          session_number_service,
                                          traffic_mirror_service,
                                          cancellation_service)

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
                                                    "actionId": "cbe6d3cb-daf3-4ec6-8a26-d2be9d500175",
                                                    "actionTarget": null,
                                                    "type": "CreateTrafficMirroring",
                                                    "actionParams": {"type": "CreateTrafficMirroringParams",
                                                                     "sourceNicId": "eni-0bf9b403bd8d36a79",
                                                                     "targetNicId": "eni-060613fdccd935b67",
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

        cancellation_context = Mock()
        cancellation_context.is_cancelled = False

        result = op.create(
            ec2_client=self.ec2_client,
            reservation=reservation,
            actions=actions,
            cancellation_context=cancellation_context,
            logger=logger,
            cloudshell=self.cloudshell)

        self.assertTrue(result.Success, 'Was not able to create traffic mirroring')
        self.fulfillments = result.Fulfillments

    # def test_manual_tests(self):
    #     res = self.cloudshell.GetResourceDetails('AWS_APP i-02181554cd72946cf')
    #     print res

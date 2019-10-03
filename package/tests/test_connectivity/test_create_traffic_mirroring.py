from unittest import TestCase
from uuid import uuid4

import boto3
from cloudshell.api.cloudshell_api import CloudShellAPISession
from mock import Mock
import logging
from cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation import \
    CreateTrafficMirroringOperation, SessionNumberService
from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.reservation_model import ReservationModel
from cloudshell.cp.core import DriverRequestParser


class TestCreateTrafficMirroring(TestCase):
    def setUp(self):
        self.cloudshell = CloudShellAPISession(host='localhost', username='admin', password='admin', domain='Global')
        self.res = self.cloudshell.CreateImmediateReservation('test', 'admin', 120).Reservation

    def tearDown(self):
        self.cloudshell.EndReservation(self.res.Id)

    def test_create_traffic_mirroring(self):
        tag_service = TagService(Mock())
        session_number_service = SessionNumberService()
        op = CreateTrafficMirroringOperation(tag_service, session_number_service)

        ec2_client = boto3.client('ec2')
        ec2_session = Mock()
        s3_session = Mock()
        reservation_context = Mock()
        reservation_context.reservation_id = self.res.Id
        reservation = ReservationModel(reservation_context)
        reservation.blueprint = 'lalala'
        reservation.owner = 'admin'
        reservation.domain = 'global'

        cp_datamodel = Mock()
        request = '''
        {
            "driverRequest": {
                                "actions": [
                                                {
                                                    "actionId": "ba7d54a5-79c3-4b55-84c2-d7d9bdc19356",
                                                    "actionTarget": null,
                                                    "type": "CreateTrafficMirroring",
                                                    "actionParams": {"type": "CreateTrafficMirroringParams",
                                                                     "sourceNicId": "eni-0fedfb8d7795f2713",
                                                                     "targetNicId": "eni-08503040f6ff30abf",
                                                                     "sessionNumber": "1",
                                                                     "filterRules": []
                                                                     }
                                                }
                                            ]
                              }
        }
        '''

        request_parser = DriverRequestParser()
        actions = request_parser.convert_driver_request_to_actions(request)
        cancellation_context = Mock()
        logger = Mock()
        logging.disable(logging.DEBUG)

        result = op.create(
            ec2_client=ec2_client,
            ec2_session=ec2_session,
            s3_session=s3_session,
            reservation=reservation,
            aws_ec2_datamodel=cp_datamodel,
            actions=actions,
            cancellation_context=cancellation_context,
            logger=logger,
            cloudshell=self.cloudshell)

        self.assertTrue(result.Success, 'Was not able to create traffic mirroring')

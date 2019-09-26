from unittest import TestCase

from cloudshell.cp.aws.domain.services.ec2.tags import TagService

from cloudshell.cp.core import DriverRequestParser
from mock import Mock

from cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation import \
    CreateTrafficMirroringOperation

import boto3


class TestCreateTrafficMirroring(TestCase):
    def test_create_traffic_mirroring(self):
        tag_service = TagService(Mock())
        op = CreateTrafficMirroringOperation(tag_service)

        ec2_client = boto3.client('ec2')
        ec2_session = Mock()
        s3_session = Mock()
        reservation = Mock()
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
                                                                     "sourceNicId": "abc",
                                                                     "targetNicId": "eni-0fedfb8d7795f2713",
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

        result = op.create(
            ec2_client=ec2_client,
            ec2_session=ec2_session,
            s3_session=s3_session,
            reservation=reservation,
            aws_ec2_datamodel=cp_datamodel,
            actions=actions,
            cancellation_context=cancellation_context,
            logger=logger)

        self.assertTrue(result.Success, 'Was not able to create traffic mirroring')

# import logging
# from unittest import TestCase
#
# import boto3
# from cloudshell.api.cloudshell_api import CloudShellAPISession
# from mock import Mock
#
# from cloudshell.cp.aws.domain.common.cancellation_service import CommandCancellationService
# from cloudshell.cp.aws.domain.conncetivity.operations.create_traffic_mirroring_operation import \
#     CreateTrafficMirrorOperation
# from cloudshell.cp.aws.domain.services.cloudshell.traffic_mirror_pool_services import SessionNumberService
# from cloudshell.cp.aws.domain.services.ec2.mirroring import TrafficMirrorService
# from cloudshell.cp.aws.domain.services.ec2.tags import TagService
# from cloudshell.cp.aws.models.reservation_model import ReservationModel
# from cloudshell.cp.core import DriverRequestParser
#
#
# class TestCreateTrafficMirroring(TestCase):
#     def setUp(self):
#         self.ec2_client = boto3.client('ec2')
#         try:
#             self.cloudshell = CloudShellAPISession(host='localhost',
#                                                    username='admin',
#                                                    password='admin',
#                                                    domain='Global')
#         except:
#             raise Exception('failed to connect to Quali Server')
#         # self.res = self.cloudshell.CreateImmediateReservation('test', 'admin', 120).Reservation
#         # reservation = self.cloudshell.CreateImmediateTopologyReservation('trafficMirrorTest', 'admin', 120,
#         #                                                    topologyFullPath='AWS-eu-west-1')
#         # while True:
#         #     self.res = self.cloudshell.GetReservationDetails(reservation.Reservation.Id).ReservationDescription
#         #     if self.res.ProvisioningStatus.lower() == 'active':
#         #         break
#         #     time.sleep(10)
#
#         self.res = self.cloudshell.GetReservationDetails('408ae027-5efe-4e33-86c8-469aa0622bfb').ReservationDescription
#
#     def tearDown(self):
#         # self.cloudshell.EndReservation(self.res.Id)
#         # TrafficMirrorCleaner.rollback(self.ec2_client, self.fulfillments)
#         pass
#
#     def test_create_traffic_mirroring(self):
#         tag_service = TagService(Mock())
#         session_number_service = SessionNumberService()
#         traffic_mirror_service = TrafficMirrorService()
#         cancellation_service = CommandCancellationService()
#         op = CreateTrafficMirrorOperation(tag_service,
#                                           session_number_service,
#                                           traffic_mirror_service,
#                                           cancellation_service)
#
#         reservation_context = Mock()
#         reservation_context.reservation_id = self.res.Id
#         reservation = ReservationModel(reservation_context)
#         reservation.blueprint = 'lalala'
#         reservation.owner = 'admin'
#         reservation.domain = 'global'
#
#         source_nic = next(next(p.Value for p in r.VmDetails.NetworkData[0].AdditionalData if p.Name=='nic') for r in self.res.Resources if 'Source' in r.Name)
#         target_nic = next(next(p.Value for p in r.VmDetails.NetworkData[0].AdditionalData if p.Name=='nic') for r in self.res.Resources if 'Target' in r.Name)
#
#         request = '''
#         {
#             "driverRequest": {
#                                 "actions": [
#                                                 {
#                                                     "actionId": "a156d3db-78fe-4c19-9039-a225d0360119",
#                                                     "actionTarget": null,
#                                                     "type": "CreateTrafficMirroring",
#                                                     "actionParams": {"type": "CreateTrafficMirroringParams",
#                                                                      "sourceNicId": "eni-0bf9b403bd8d36a79",
#                                                                      "targetNicId": "eni-060613fdccd935b67",
#                                                                      "sessionNumber": "3",
#                                                                      "filterRules": [
#                                                                         {
#                                                                             "type": "TrafficFilterRule",
#                                                                             "direction": "ingress",
#                                                                             "sourcePortRange": {
#                                                                                 "type": "PortRange",
#                                                                                 "fromPort": "123",
#                                                                                 "toPort": "123"
#                                                                             },
#                                                                             "protocol": "tcp"
#                                                                         }
#                                                                      ]
#                                                                      }
#                                                 }
#                                             ]
#                               }
#         }
#         '''
#
#         request_parser = DriverRequestParser()
#         actions = request_parser.convert_driver_request_to_actions(request)
#         logger = Mock()
#         actions[0].actionParams.sourceNicId = source_nic
#         actions[0].actionParams.targetNicId = target_nic
#
#         logging.disable(logging.DEBUG)
#
#         cancellation_context = Mock()
#         cancellation_context.is_cancelled = False
#
#         results = op.create(
#             ec2_client=self.ec2_client,
#             reservation=reservation,
#             actions=actions,
#             cancellation_context=cancellation_context,
#             logger=logger,
#             cloudshell=self.cloudshell)
#
#         self.assertTrue(next(r.success for r in results)==True,
#                         'Was not able to create traffic mirroring')
#
#
# #  def test_manual_tests(self):
# #     res = self.cloudshell.GetResourceDetails('AWS_APP i-02181554cd72946cf')
# #     print res
#

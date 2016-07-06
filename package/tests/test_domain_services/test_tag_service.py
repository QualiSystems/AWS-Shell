from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class TestTagService(TestCase):
    def setUp(self):
        self.tag_service = TagService()

    def test_get_security_group_tags(self):
        reservation = ReservationModel()
        reservation.reservation_id = 'ReservationId'
        reservation.owner = 'Owner'
        reservation.blueprint = 'Blueprint'
        reservation.domain = 'Global'
        res = self.tag_service.get_security_group_tags('name', 'shared', reservation)
        self.assertEqual(res, [{'Value': 'name', 'Key': 'Name'},
                               {'Value': 'Cloudshell', 'Key': 'CreatedBy'},
                               {'Value': 'Blueprint', 'Key': 'Blueprint'},
                               {'Value': 'Owner', 'Key': 'Owner'},
                               {'Value': 'Global', 'Key': 'Domain'},
                               {'Value': 'ReservationId', 'Key': 'ReservationId'},
                               {'Value': 'shared', 'Key': 'Isolation'}])

    def test_set_ec2_resource_tag(self):
        resource = Mock()
        tags = Mock()

        self.tag_service.set_ec2_resource_tags(resource, tags)

        self.assertTrue(resource.create_tags.called_with(tags))
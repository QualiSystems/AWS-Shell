from unittest import TestCase

from mock import Mock, MagicMock

from cloudshell.cp.aws.domain.services.ec2.tags import TagService
from cloudshell.cp.aws.models.reservation_model import ReservationModel


class TestTagService(TestCase):
    def setUp(self):
        self.tag_service = TagService(MagicMock())

    def test_get_security_group_tags(self):
        reservation_context = Mock()
        reservation_context.reservation_id = 'ReservationId'
        reservation_context.owner_user = 'Owner'
        reservation_context.environment_name = 'Blueprint'
        reservation_context.domain = 'Global'

        reservation = ReservationModel(reservation_context)

        res = self.tag_service.get_security_group_tags('name', 'shared', reservation, 'InboundPorts')
        self.assertEqual(res, [{'Value': 'name', 'Key': 'Name'},
                               {'Value': 'Cloudshell', 'Key': 'CreatedBy'},
                               {'Value': 'Blueprint', 'Key': 'Blueprint'},
                               {'Value': 'Owner', 'Key': 'Owner'},
                               {'Value': 'Global', 'Key': 'Domain'},
                               {'Value': 'ReservationId', 'Key': 'ReservationId'},
                               {'Value': 'shared', 'Key': 'Isolation'},
                               {'Value': 'InboundPorts', 'Key': 'Type'}])

    def test_get_default_tags(self):
        reservation_context = Mock()
        reservation_context.reservation_id = 'ReservationId'
        reservation_context.owner_user = 'Owner'
        reservation_context.environment_name = 'Blueprint'
        reservation_context.domain = 'Global'

        reservation = ReservationModel(reservation_context)

        res = self.tag_service.get_default_tags(name='name', reservation=reservation)

        self.assertEqual(res, [{'Value': 'name', 'Key': 'Name'},
                               {'Value': 'Cloudshell', 'Key': 'CreatedBy'},
                               {'Value': 'Blueprint', 'Key': 'Blueprint'},
                               {'Value': 'Owner', 'Key': 'Owner'},
                               {'Value': 'Global', 'Key': 'Domain'},
                               {'Value': 'ReservationId', 'Key': 'ReservationId'}])

    def test_set_ec2_resource_tag(self):
        resource = Mock()
        tags = [Mock()]

        self.tag_service.set_ec2_resource_tags(resource=resource, tags=tags)

        self.assertTrue(resource.create_tags.called_with(tags))

    def test_find_isolation_tag_value(self):
        tag1 = MagicMock()
        tag2 = {'Key': 'Isolation', 'Value': 'Shared'}
        tags = [tag1, tag2]

        value = self.tag_service.find_isolation_tag_value(tags=tags)

        self.assertEquals(value, 'Shared')

    def test_get_is_public_tag(self):
        # Arrange
        public_value = "False"

        # Act
        public_tag = self.tag_service.get_is_public_tag(public_value)

        # Assert
        self.assertEquals(public_tag, {'Key': 'IsPublic', 'Value': public_value})

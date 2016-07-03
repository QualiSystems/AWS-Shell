from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.tags import TagService


class TestTagService(TestCase):
    def setUp(self):
        self.tag_service = TagService()

    def test_get_security_group_tags(self):
        res = self.tag_service.get_security_group_tags('name', 'shared', 'res_id')
        self.assertEqual(res, [{'Value': 'name', 'Key': 'Name'},
                               {'Value': 'Quali', 'Key': 'CreatedBy'},
                               {'Value': 'res_id', 'Key': 'ReservationId'},
                               {'Value': 'shared', 'Key': 'Isolation'}])

    def test_set_ec2_resource_tag(self):
        resource = Mock()
        tags = Mock()

        self.tag_service.set_ec2_resource_tags(resource, tags)

        self.assertTrue(resource.create_tags.called_with(tags))
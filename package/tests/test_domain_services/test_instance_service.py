from unittest import TestCase

from mock import Mock

from cloudshell.cp.aws.domain.services.ec2.instance import InstanceService


class TestInstanceService(TestCase):
    def setUp(self):
        self.tag_service = Mock()
        self.instance_waiter = Mock()
        self.ec2_session = Mock()
        self.name = 'name'
        self.reservation_id = 'res_id'
        self.instance = Mock()
        self.instance.instance_id = 'id'
        self.default_tags = ['tag1', 'tag2']
        self.tag_service.get_default_tags = Mock(return_value=self.default_tags)
        self.ec2_session.create_instances = Mock(return_value=[self.instance])
        self.instance_service = InstanceService(self.tag_service, self.instance_waiter)

    def test_create_instance(self):
        ami_dep = Mock()
        res = self.instance_service.create_instance(ec2_session=self.ec2_session,
                                                    name=self.name,
                                                    reservation=self.reservation_id,
                                                    ami_deployment_info=ami_dep)
        self.assertTrue(self.ec2_session.create_instances.called_with(ami_dep.aws_ami_id,
                                                                      ami_dep.min_count,
                                                                      ami_dep.max_count,
                                                                      ami_dep.instance_type,
                                                                      ami_dep.aws.key,
                                                                      ami_dep.block_device_mappings,
                                                                      [
                                                                          {
                                                                              'SubnetId': ami_dep.subnet_id,
                                                                              'DeviceIndex': 0,
                                                                              'Groupd': ami_dep.security_group_ids
                                                                          }
                                                                      ]))
        self.assertTrue(self.tag_service.get_default_tags.called_with(self.name + ' ' + self.reservation_id,
                                                                      self.reservation_id))
        self.assertTrue(self.tag_service.set_ec2_resource_tags.called_with(self.instance, self.default_tags))
        self.assertTrue(self.instance.load.called)
        self.assertEqual(self.instance, res)

    def test_get_instance_by_id(self):
        res = self.instance_service.get_instance_by_id(self.ec2_session, 'id')
        self.assertTrue(self.ec2_session.Instance.called_with('id'))
        self.assertIsNotNone(res)

    def test_terminate_instance(self):
        self.instance_waiter.multi_wait = Mock(return_value=[self.instance])
        res = self.instance_service.terminate_instance(self.instance)

        self.assertTrue(self.instance.terminate.called)
        self.assertTrue(self.instance_waiter.multi_wait.called_with([self.instance], 'terminated'))
        self.assertIsNotNone(res)

    def test_terminate_instances(self):
        instances = [Mock(), Mock()]
        res = self.instance_service.terminate_instances(instances)

        self.assertTrue(instances[0].terminate.called)
        self.assertTrue(instances[1].terminate.called)
        self.assertTrue(self.instance_waiter.multi_wait.called_with([self.instance], 'terminated'))
        self.assertIsNotNone(res)
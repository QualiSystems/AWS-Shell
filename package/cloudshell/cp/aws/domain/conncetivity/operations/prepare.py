from cloudshell.cp.aws.domain.services.ec2.tags import *
from cloudshell.cp.aws.models.connectivity_models import PrepareConnectivityActionResult
from cloudshell.cp.aws.models.port_data import PortData

INVALID_REQUEST_ERROR = 'Invalid request: {0}'


class PrepareConnectivityOperation(object):
    def __init__(self, vpc_service, security_group_service, key_pair_service, tag_service):
        """
        :param vpc_service: VPC Service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc_service.VPCService
        :param security_group_service:
        :type security_group_service: clousdhell.cp.aws.domain.services.ec2.security_group.SecurityGroupService
        :param key_pair_service:
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        :param tag_service:
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        """
        self.vpc_service = vpc_service
        self.security_group_service = security_group_service
        self.key_pair_service = key_pair_service
        self.tag_service = tag_service

    def prepare_connectivity(self, ec2_session, s3_session, reservation_id, aws_ec2_datamodel, request):
        """
        Will create a vpc for the reservation and will peer it to the management vpc
        also will create a key pair for that reservation
        :param ec2_session: EC2 Session
        :param s3_session: S3 Session
        :param reservation_id: The reservation ID
        :type reservation_id: str
        :param aws_ec2_datamodel: The AWS EC2 data model
        :type aws_ec2_datamodel: cloudshell.cp.aws.models.aws_ec2_cloud_provider_resource_model.AWSEc2CloudProviderResourceModel
        :param request: Parsed prepare connectivity request
        :return:
        """
        if not aws_ec2_datamodel.management_vpc_id:
            raise ValueError('Management VPC ID must be set!')

        self._create_key_pair(ec2_session=ec2_session,
                              s3_session=s3_session ,
                              bucket=aws_ec2_datamodel.key_pairs_location,
                              reservation_id=reservation_id)
        results = []
        for action in request.actions:
            try:
                # will get or create a vpc for the reservation
                vpc = self._get_or_create_vpc(action, ec2_session, reservation_id)

                self._peer_vpcs(ec2_session, aws_ec2_datamodel.management_vpc_id, vpc.id)

                security_group = self._get_or_create_security_group(ec2_session=ec2_session,
                                                                    reservation_id=reservation_id,
                                                                    vpc=vpc,
                                                                    management_sg_id=aws_ec2_datamodel.management_sg_id)

                results.append(self._create_action_result(action, security_group, vpc))

            except Exception as e:
                results.append(self._create_fault_action_result(action, e))
        return results

    def _create_key_pair(self, ec2_session, s3_session, bucket, reservation_id):
        keypair = self.key_pair_service.get_key_for_reservation(s3_session=s3_session,
                                                                bucket_name=bucket,
                                                                reservation_id=reservation_id)
        if not keypair:
            self.key_pair_service.create_key_pair(ec2_session=ec2_session,
                                                  s3_session=s3_session,
                                                  bucket=bucket,
                                                  reservation_id=reservation_id)

    def _peer_vpcs(self, ec2_session, management_vpc_id, vpc_id):
        self.vpc_service.peer_vpcs(ec2_session=ec2_session,
                                   vpc_id1=management_vpc_id,
                                   vpc_id2=vpc_id)

    def _get_or_create_security_group(self, ec2_session, reservation_id, vpc, management_sg_id):
        sg_name = self.security_group_service.get_sandbox_security_group_name(reservation_id)
        security_group = self.security_group_service.get_security_group_by_name(vpc=vpc, name=sg_name)

        if not security_group:
            security_group = \
                self.security_group_service.create_security_group(ec2_session=ec2_session,
                                                                  vpc_id=vpc.id,
                                                                  security_group_name=sg_name)

            tags = self.tag_service.get_security_group_tags(name=sg_name,
                                                            isolation=IsolationTagValues.Shared,
                                                            reservation_id=reservation_id)
            self.tag_service.set_ec2_resource_tags(security_group, tags)

            self.security_group_service.set_shared_reservation_security_group_rules(security_group=security_group,
                                                                                    management_sg_id=management_sg_id)

        return security_group

    def _get_or_create_vpc(self, action, ec2_session, reservation_id):
        cidr = self._extract_cidr(action)
        vpc = self.vpc_service.find_vpc_for_reservation(ec2_session=ec2_session,
                                                        reservation_id=reservation_id)
        if not vpc:
            vpc = self.vpc_service.create_vpc_for_reservation(ec2_session=ec2_session,
                                                              reservation_id=reservation_id,
                                                              cidr=cidr)
        return vpc

    @staticmethod
    def _create_action_result(action, security_group, vpc):
        action_result = PrepareConnectivityActionResult()
        action_result.actionId = action.actionId
        action_result.success = True
        action_result.infoMessage = 'PrepareConnectivity finished successfully'
        action_result.vpcId = vpc.id
        action_result.securityGroupId = security_group.id
        return action_result

    @staticmethod
    def _extract_cidr(action):
        cidrs = [custom_attribute.attributeValue
                 for custom_attribute in action.customActionAttributes
                 if custom_attribute.attributeName == 'Network']
        if not cidrs:
            raise ValueError(INVALID_REQUEST_ERROR.format('CIDR is missing'))
        if len(cidrs) > 1:
            raise ValueError(INVALID_REQUEST_ERROR.format('Too many CIDRs parameters were found'))
        return cidrs[0]

    @staticmethod
    def _create_fault_action_result(action, e):
        action_result = PrepareConnectivityActionResult()
        action_result.actionId = action.actionId
        action_result.success = False
        action_result.errorMessage = 'PrepareConnectivity ended with the error: {0}'.format(e)
        return action_result

    def _get_sandbox_security_group_inbound_rules(self, management_vpc_id):
        return [PortData(3389, 3389, 'TCP', management_vpc_id),  # RDP
                PortData(3389, 3389, 'UDP', management_vpc_id),  # RDP
                PortData(22, 22, 'TCP', management_vpc_id),  # SSH
                ]

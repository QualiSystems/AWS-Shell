

class CleanupConnectivityOperation(object):
    def __init__(self, vpc_service, key_pair_service):
        """
        :param vpc_service: VPC Service
        :type vpc_service: cloudshell.cp.aws.domain.services.ec2.vpc.VPCService
        :param key_pair_service: Security Group Service
        :type key_pair_service: cloudshell.cp.aws.domain.services.ec2.keypair.KeyPairService
        """
        self.vpc_service = vpc_service
        self.key_pair_service = key_pair_service

    def cleanup(self, ec2_session, s3_session, bucket_name, reservation_id):
        result = {'success': True}
        try:
            vpc = self.vpc_service.find_vpc_for_reservation(ec2_session, reservation_id)
            if not vpc:
                raise ValueError('No VPC was created for this reservation')

            self.vpc_service.delete_all_instances(vpc)
            self.key_pair_service.remove_key_pair_for_reservation(s3_session, bucket_name, reservation_id)
            self.vpc_service.remove_all_security_groups(vpc)
            self.vpc_service.remove_all_subnets(vpc)
            self.vpc_service.remove_all_internet_gateways(vpc)
            self.vpc_service.remove_all_peering(vpc)

            self.vpc_service.delete_vpc(vpc)
        except Exception as exc:
            result['success'] = False
            result['errorMessage'] = 'PrepareConnectivity ended with the error: {0}'.format(exc)

        return result

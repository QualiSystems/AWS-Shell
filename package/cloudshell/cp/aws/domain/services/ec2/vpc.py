VPC_RESERVATION = 'VPC Reservation: {0}'


class VPCService(object):
    def __init__(self, tag_service):
        """
        :param tag_service: Tag Service
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tag_creator.TagService
        :return:
        """
        self.tag_service = tag_service

    def create_vpc_for_reservation(self, ec2_session, reservation_id, cidr):
        """
        Will create a vpc for reservation and will save it in a folder in the s3 bucket
        :param ec2_session: Ec2 Session
        :param reservation_id: Reservation ID
        :type reservation_id: str
        :param cidr: The CIDR block
        :type cidr: str
        :return: vpc
        """
        vpc = ec2_session.create_vpc(CidrBlock=cidr)

        # TODO: vpc check status if needed

        self._set_tags(reservation_id, vpc)
        # self.s3_service.save_to_reservation_bucket(s3_bucket_name, reservation_id, vpc.id)
        return vpc

    @staticmethod
    def find_vpc_for_reservation(ec2_session, reservation_id):
        filters = [{'Name': 'tag:Name',
                    'Values': [VPC_RESERVATION.format(reservation_id)]}]

        vpcs = list(ec2_session.vpcs.filter(Filters=filters))

        if not vpcs:
            return None

        if len(vpcs) > 1:
            raise ValueError('Too many vpcs for the reservation')

        return vpcs[0]

    def peer_vpcs(self, ec2_session, vpc_id1, vpc_id2):
        """
        Will create a peering between vpc to the other
        :param ec2_session: EC2 session
        :param vpc_id1: VPC Id
        :type vpc_id1: str
        :param vpc_id2: VPC Id
        :type vpc_id2: str
        :param reservation_id: The reservation id
        :type reservation_id: str
        :return: vpc peering id
        """
        vpc_peer_connection = ec2_session.create_vpc_peering_connection(VpcId=vpc_id1, PeerVpcId=vpc_id2)
        return vpc_peer_connection.id

    def _set_tags(self, reservation_id, resource):
        tags = self.tag_service.get_default_tags(VPC_RESERVATION.format(reservation_id), reservation_id)
        self.tag_service.set_ec2_resource_tags(resource, tags)

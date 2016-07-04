from cloudshell.cp.aws.domain.services.waiters.vpc_peering import VpcPeeringConnectionWaiter
class VPCService(object):
    VPC_RESERVATION = 'VPC Reservation: {0}'

    def __init__(self, tag_service, subnet_service, instance_service, vpc_waiter, vpc_peering_waiter):
        """
        :param tag_service: Tag Service
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        :param subnet_service: Subnet Service
        :type subnet_service: cloudshell.cp.aws.domain.services.ec2.subnet.SubnetService
        :param instance_service: Instance Service
        :type instance_service: cloudshell.cp.aws.domain.services.ec2.instance.InstanceService
        :param vpc_waiter: Vpc Peering Connection Waiter
        :type vpc_waiter: cloudshell.cp.aws.domain.services.waiters.vpc.VPCWaiter
        :param vpc_peering_waiter: Vpc Peering Connection Waiter
        :type vpc_peering_waiter: cloudshell.cp.aws.domain.services.waiters.vpc_peering.VpcPeeringConnectionWaiter
        """
        self.tag_service = tag_service
        self.subnet_service = subnet_service
        self.instance_service = instance_service
        self.vpc_waiter = vpc_waiter
        self.vpc_peering_waiter = vpc_peering_waiter

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

        self.vpc_waiter.wait(vpc, self.vpc_waiter.RUNNING)

        vpc_name = self.VPC_RESERVATION.format(reservation_id)
        self._set_tags(vpc_name=vpc_name, reservation_id=reservation_id, vpc=vpc)

        self.subnet_service.create_subnet_for_vpc(vpc=vpc, cidr=cidr, vpc_name=vpc_name, reservation_id=reservation_id)
        return vpc

    def find_vpc_for_reservation(self, ec2_session, reservation_id):
        filters = [{'Name': 'tag:Name',
                    'Values': [self.VPC_RESERVATION.format(reservation_id)]}]

        vpcs = list(ec2_session.vpcs.filter(Filters=filters))

        if not vpcs:
            return None

        if len(vpcs) > 1:
            raise ValueError('Too many vpcs for the reservation')

        return vpcs[0]

    def peer_vpcs(self, ec2_session, vpc_id1, vpc_id2):
        """
        Will create a peering request between 2 vpc's and approve it
        :param ec2_session: EC2 session
        :param vpc_id1: VPC Id
        :type vpc_id1: str
        :param vpc_id2: VPC Id
        :type vpc_id2: str
        :return: vpc peering id
        """
        vpc_peer_connection = ec2_session.create_vpc_peering_connection(VpcId=vpc_id1, PeerVpcId=vpc_id2)

        # wait until pending acceptance
        self.vpc_peering_waiter.wait(vpc_peer_connection, self.vpc_peering_waiter.PENDING_ACCEPTANCE)

        vpc_peer_connection.accept()

        # wait until connection active
        self.vpc_peering_waiter.wait(vpc_peer_connection, self.vpc_peering_waiter.ACTIVE)

        return vpc_peer_connection.id

    def _set_tags(self, vpc_name, reservation_id, vpc):
        tags = self.tag_service.get_default_tags(vpc_name, reservation_id)
        self.tag_service.set_ec2_resource_tags(vpc, tags)

    def remove_all_internet_gateways(self, vpc):
        """
        Removes all internet gateways from a VPC
        :param vpc: EC2 VPC instance
        """
        internet_gateways = self.get_all_internet_gateways(vpc)
        for ig in internet_gateways:
            ig.detach_from_vpc(VpcId=vpc.id)
            ig.delete()

    def get_all_internet_gateways(self, vpc):
        """
        :param vpc:
        :return:
        :rtype: list
        """
        return list(vpc.internet_gateways.all())

    def create_and_attach_internet_gateway(self, ec2_session, vpc, reservation_id):
        internet_gateway = ec2_session.create_internet_gateway()

        tags = self.tag_service.get_default_tags("IGW {0}".format(reservation_id), reservation_id)

        self.tag_service.set_ec2_resource_tags(
                resource=internet_gateway,
                tags=tags)

        vpc.attach_internet_gateway(InternetGatewayId=internet_gateway.id)

    def remove_all_peering(self, vpc):
        """
        Remove all peering to that VPC
        :param vpc: EC2 VPC instance
        :return:
        """
        peerings = list(vpc.accepted_vpc_peering_connections.all())
        for peer in peerings:
            if peer.status['Code'] != 'failed':
                peer.delete()
        return True

    def remove_all_security_groups(self, vpc):
        """
        Will remove all security groups to the VPC
        :param vpc: EC2 VPC instance
        :return:
        """
        security_groups = list(vpc.security_groups.all())
        for sg in security_groups:
            if sg.group_name != 'default':
                sg.delete()
        return True

    def remove_all_subnets(self, vpc):
        """
        Will remove all attached subnets to that vpc
        :param vpc: EC2 VPC instance
        :return:
        """
        subnets = list(vpc.subnets.all())
        for subnet in subnets:
            self.subnet_service.detele_subnet(subnet)
        return True

    def delete_all_instances(self, vpc):
        instances = list(vpc.instances.all())
        self.instance_service.terminate_instances(instances)
        return True

    def delete_vpc(self, vpc):
        """
        Will delete the vpc instance
        :param vpc: VPC instance
        :return:
        """
        vpc.delete()
        return True

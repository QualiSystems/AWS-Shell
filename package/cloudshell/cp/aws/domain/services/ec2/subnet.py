SUBNET_NAME = 'VPC Name: {0}'


class SubnetService(object):
    def __init__(self, tag_service, subnet_waiter):
        """
        :param tag_service: Tag service
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        :param subnet_waiter: Subnet waiter
        :type subnet_waiter: cloudshell.cp.aws.domain.services.waiters.subnet.SubnetWaiter
        """
        self.tag_service = tag_service
        self.subnet_waiter = subnet_waiter

    def create_subnet_for_vpc(self, vpc, cidr, vpc_name, reservation):
        """
        Will create a subnet for the given vpc
        :param reservation: reservation model
        :type reservation: cloudshell.cp.aws.models.reservation_model.ReservationModel
        :param vpc: VPC instanve
        :param cidr: CIDR
        :type cidr: str
        :param vpc_name: The vpc name
        :type vpc_name: str
        :return:
        """
        subnet = vpc.create_subnet(CidrBlock=cidr)
        self.subnet_waiter.wait(subnet, self.subnet_waiter.AVAILABLE)

        subnet_name = self._get_subnet_name(vpc_name)
        tags = self.tag_service.get_default_tags(subnet_name, reservation)

        self.tag_service.set_ec2_resource_tags(subnet, tags)
        return subnet

    def get_vpc_subnets(self, vpc):
        subnets = list(vpc.subnets.all())
        if not subnets:
            raise ValueError('The given VPC({0}) has no subnets'.format(vpc.id))
        return subnets

    @staticmethod
    def get_first_subnet_from_vpc(vpc):
        subnets = list(vpc.subnets.all())
        if not subnets:
            raise ValueError('The given VPC({0}) has no subnet'.format(vpc.id))
        return subnets[0]

    @staticmethod
    def _get_subnet_name(name):
        return SUBNET_NAME.format(name)

    def detele_subnet(self, subnet):
        subnet.delete()
        return True

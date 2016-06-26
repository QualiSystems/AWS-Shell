SUBNET_NAME = 'vpc name: {0}'


class SubnetService(object):
    def __init__(self, tag_service):
        """
        :param tag_service: Tag service
        :type tag_service: cloudshell.cp.aws.domain.services.ec2.tags.TagService
        """
        self.tag_service = tag_service

    def create_subnet_for_vpc(self, vpc, cidr, vpc_name):
        """
        Will create a subnet for the given vpc
        :param vpc: VPC instanve
        :param cidr: CIDR
        :type cidr: str
        :param vpc_name: The vpc name
        :type vpc_name: str
        :return:
        """
        subnet = vpc.create_subnet(CidrBlock=cidr)
        subnet_name = self._get_subnet_name(vpc_name)

        tags = [self.tag_service.get_created_by_kvp(),
                self.tag_service.get_name_tag(subnet_name)]

        self.tag_service.set_ec2_resource_tags(subnet, tags)
        return subnet

    @staticmethod
    def get_subnet_from_vpc(vpc):
        subnets = list(vpc.subnets.all())
        if not subnets:
            raise ValueError('The given VPC({0}) has no subnet'.format(vpc.id))
        return subnets[0]

    @staticmethod
    def _get_subnet_name(name):
        return SUBNET_NAME.format(name)

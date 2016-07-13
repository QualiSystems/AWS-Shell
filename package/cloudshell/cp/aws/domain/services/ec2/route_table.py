class RouteTablesService(object):
    def __init__(self):
        pass

    def get_all_route_tables(self, ec2_session, vpc_id):
        """
        :param ec2_session: Ec2 Session
        :param vpc_id:
        :return:
        """
        vpc = ec2_session.Vpc(vpc_id)
        return list(vpc.route_tables.all())

    def get_main_route_table(self, ec2_session, vpc_id):
        """
        Return the main route table of the given VPC
        :param ec2_session: Ec2 Session
        :param vpc_id:
        :return:
        """
        rt_all = self.get_all_route_tables(ec2_session, vpc_id)
        for rt in rt_all:
            if rt.associations_attribute:
                for association_att in rt.associations_attribute:
                    if 'Main' in association_att and association_att['Main'] == True:
                        return rt
        return None

    def add_route_to_peered_vpc(self, route_table, target_peering_id, target_vpc_cidr):
        """

        :param route_table: RouteTable ec2 object
        :param str target_peering_id: VPC Peering Connection Id for the route target
        :param str target_vpc_cidr: CIDR block for the route destination
        :return:
        """
        route_table.create_route(DestinationCidrBlock=target_vpc_cidr, VpcPeeringConnectionId=target_peering_id)








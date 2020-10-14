class RouteTablesService(object):
    def __init__(self, tag_service):
        """
        :param tag_service: Tag Service
        """
        self.tag_service = tag_service

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

    def add_route_to_internet_gateway(self, route_table, target_internet_gateway_id):
        """
        :param route_table: RouteTable ec2 object
        :param str target_internet_gateway_id: Id for the route target
        :param str target_vpc_cidr: CIDR block for the route destination
        :return:
        """
        route_table.create_route(GatewayId=target_internet_gateway_id, DestinationCidrBlock='0.0.0.0/0')

    def find_first_route(self, route_table, filters):
        """
        :param route_table:
        :param dict filters:
        :return: return a route object
        """
        for route in route_table.routes:
            all_filter_ok = True
            for key in filters:
                if type(route) is dict:
                    if not(key in route and route[key] == filters[key]):
                        all_filter_ok = False
                        break
                else:
                    if not(hasattr(route, key) and getattr(route, key) == filters[key]):
                        all_filter_ok = False
                        break
            if all_filter_ok:
                return route
        return None

    def delete_blackhole_routes(self, route_table, ec2_client=None):
        """
        Removes all routes in in route_table that have status blackhole
        :param route_table:
        :return:
        """
        for route in route_table.routes:
            if hasattr(route, 'state') and route.state == 'blackhole':
                try:
                    route.delete()
                except Exception as e:
                    if 'InvalidRoute.NotFound' in str(e):
                        # ignore this error if the route was not found
                        pass
                    else:
                        raise e
            if ec2_client and isinstance(route, dict) and route.get('State') == 'blackhole':
                try:
                    ec2_client.delete_route(RouteTableId=route_table.id, DestinationCidrBlock=route['DestinationCidrBlock'])
                except Exception as e:
                    if 'InvalidRoute.NotFound' in str(e):
                        # ignore this error if the route was not found
                        pass
                    else:
                        raise e

    def replace_route(self, route_table, route, peer_connection_id, ec2_client):
        if type(route) is dict:
            ec2_client.replace_route(RouteTableId=route_table.id, DestinationCidrBlock=route['DestinationCidrBlock'],
                                     VpcPeeringConnectionId=peer_connection_id)
        else:
            route.replace(VpcPeeringConnectionId=peer_connection_id)


    def get_custom_route_tables(self, ec2_session, vpc_id):
        """
        :param ec2_session: Ec2 Session
        :param vpc: EC2 VPC instance
        :return:
        """
        main_table = self.get_main_route_table(ec2_session, vpc_id)
        all_tables = self.get_all_route_tables(ec2_session, vpc_id)
        custom_tables = [t for t in all_tables if t.id != main_table.id]
        return custom_tables

    def delete_table(self, table):
        table.delete()
        return True

    def create_route_table(self, ec2_session, reservation, vpc_id, table_name):
        """
        :param ec2_session: Ec2 Session
        :param vpc_id:
        :return:
        """
        vpc = ec2_session.Vpc(vpc_id)
        route_table = vpc.create_route_table()
        tags = self.tag_service.get_default_tags(table_name, reservation)
        self.tag_service.set_ec2_resource_tags(route_table, tags)
        return route_table

    def get_route_table(self, ec2_session, vpc_id, table_name):
        """
        :param ec2_session: Ec2 Session
        :param str vpc_id:
        :param str table_name:
        :return:
        """
        tables = self.get_all_route_tables(ec2_session, vpc_id)
        for table in tables:
            for tag in table.tags:
                if tag["Key"] == "Name" and tag["Value"] == table_name:
                    return table
        return None
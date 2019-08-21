import jsonpickle

from cloudshell.cp.aws.models.network_actions_models import RouteTableRequestResourceModel, RouteResourceModel


class AWSModelParser(object):

    @staticmethod
    def convert_to_route_table_model(route_table_request):
        """
        Convert JSON request

        :param str route_table_request: JSON string
        :rtype: list[RouteTableRequestResourceModel]
        """
        data = jsonpickle.decode(route_table_request)
        route_table_models = []
        for route_table in data.get('route_tables', []):
            route_table_model = RouteTableRequestResourceModel()
            route_table_model.name = route_table.get('name', route_table_model.name)
            route_table_model.subnets = route_table.get('subnets', [])
            for route in route_table.get('routes', []):
                route_model = RouteResourceModel()
                for attr, value in vars(route_model).items():
                    setattr(route_model, attr, route.get(attr, value))
                route_table_model.routes.append(route_model)
            route_table_models.append(route_table_model)

        return route_table_models

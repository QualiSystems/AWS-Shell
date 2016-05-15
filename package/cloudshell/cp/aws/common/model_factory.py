class ResourceModelParser(object):
    def __init__(self):
        pass

    def convert_to_resource_model(self, resource_instance, resource_model_type):
        """
        Converts an instance of resource with dictionary of attributes
        to a class instance according to family and assigns its properties
        :param resource_instance: Instance of resource
        :param resource_model_type: Resource Model type to create
        :return:
        """
        if resource_model_type:
            if not callable(resource_model_type):
                raise ValueError('resource_model_type {0} cannot be instantiated'.format(resource_model_type))
            instance = resource_model_type()
        else:
            instance = ResourceModelParser.create_resource_model_instance(resource_instance)
        props = ResourceModelParser.get_public_properties(instance)
        for attrib in ResourceModelParser.get_resource_attributes(resource_instance):
            property_name = ResourceModelParser.get_property_name_from_attribute_name(attrib)
            property_name_for_attribute_name = ResourceModelParser.get_property_name_with_attribute_name_postfix(attrib)
            if props.__contains__(property_name):
                value = self.get_attribute_value(attrib, resource_instance)
                setattr(instance, property_name, value)
                if hasattr(instance, property_name_for_attribute_name):
                    setattr(instance, property_name_for_attribute_name, attrib)
                    props.remove(property_name_for_attribute_name)
                props.remove(property_name)

        if props:
            raise ValueError('Property(ies) {0} not found on resource with attributes {1}'
                             .format(','.join(props),
                                     ','.join(ResourceModelParser.get_resource_attributes(resource_instance))))
        return instance
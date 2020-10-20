def convert_to_bool(string):
    """
    Converts string to bool
    :param string: String
    :str string: str
    :return: True or False
    """
    if isinstance(string, bool):
        return string
    return string in ['true', 'True', '1']

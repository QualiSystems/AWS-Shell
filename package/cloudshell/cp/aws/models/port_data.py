class PortData(object):
    def __init__(self, from_port, to_port, protocol, destination):
        """ec2_session

        :param from_port: to_port-start port
        :type from_port: int
        :param to_port: from_port-end port
        :type to_port: int
        :param protocol: protocol-can be UDP or TCP
        :type protocol: str
        :param destination: Determines the traffic that can leave your instance, and where it can go.
        :type destination: str
        :return:
        """
        self.from_port = from_port
        self.to_port = to_port
        self.protocol = protocol
        self.destination = destination

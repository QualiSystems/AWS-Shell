from unittest import TestCase

from cloudshell.cp.aws.domain.services.parsers.aws_model_parser import AWSModelsParser


class TestModelParser(TestCase):
    def setUp(self):
        pass

    def test_parse_public_ip_options_attribute_elastic(self):
        # arrange
        public_ip_options_val = "Elastic IPs"

        # act
        (public, elastic) = AWSModelsParser.parse_public_ip_options_attribute(public_ip_options_val)

        # assert
        self.assertFalse(public)
        self.assertTrue(elastic)

    def test_parse_public_ip_options_attribute_public(self):
        # arrange
        public_ip_options_val = "Public IP"

        # act
        (public, elastic) = AWSModelsParser.parse_public_ip_options_attribute(public_ip_options_val)

        # assert
        self.assertTrue(public)
        self.assertFalse(elastic)

    def test_parse_public_ip_options_attribute_no_public_ip(self):
        # arrange
        public_ip_options_val = "No Public IP"

        # act
        (public, elastic) = AWSModelsParser.parse_public_ip_options_attribute(public_ip_options_val)

        # assert
        self.assertFalse(public)
        self.assertFalse(elastic)

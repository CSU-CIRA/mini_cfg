import pathlib
import unittest

from mini_cfg import mini_cfg
from tests.itests import file_test_suite

BASIC_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/yaml/basic_config.yaml")
NESTED_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/yaml/nested_config.yaml")
CASCADE_CONFIG_FILE = pathlib.Path(
    "tests/itests/test_configs/yaml/cascaded_config.yaml"
)
NESTED_WITH_POINTER_FILE = pathlib.Path(
    "tests/itests/test_configs/yaml/nested_with_pointer_config.yaml"
)


class Test_YAMLSuite(unittest.TestCase):
    def test_yaml(self):
        fix = file_test_suite.TestFixture(
            mini_cfg._read_yaml,
            self,
            BASIC_CONFIG_FILE,
            NESTED_CONFIG_FILE,
            CASCADE_CONFIG_FILE,
            NESTED_WITH_POINTER_FILE,
        )
        file_test_suite.perform_tests(fix)

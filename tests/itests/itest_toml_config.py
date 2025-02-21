import pathlib
import unittest

from mini_cfg import mini_cfg
from tests.itests import file_test_suite

BASIC_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/toml/basic_config.toml")
NESTED_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/toml/nested_config.toml")
CASCADE_CONFIG_FILE = pathlib.Path(
    "tests/itests/test_configs/toml/cascaded_config.toml"
)
NESTED_WITH_POINTER_FILE = pathlib.Path(
    "tests/itests/test_configs/toml/nested_with_pointer_config.toml"
)
NESTED_WITH_POINTER_CYCLE = pathlib.Path(
    "tests/itests/test_configs/toml/nested_cycle_a.toml"
)


class Test_TOMLSuite(unittest.TestCase):
    def test_toml(self):
        fix = file_test_suite.TestFixture(
            mini_cfg._read_toml,
            self,
            BASIC_CONFIG_FILE,
            NESTED_CONFIG_FILE,
            CASCADE_CONFIG_FILE,
            NESTED_WITH_POINTER_FILE,
            NESTED_WITH_POINTER_CYCLE,
        )
        file_test_suite.perform_tests(fix)

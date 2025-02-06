import dataclasses
import datetime as dt
import pathlib
import unittest

from mini_cfg import mini_cfg

BASIC_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/basic_config.toml")

TEST_DATE = dt.datetime(2025, 2, 6, 12, 5, 1)
PARTIAL_DATE = dt.datetime(2025, 2, 6)
PARTIAL_DATE_AS_DATE = dt.date(2025, 2, 6)
TEST_PATH = pathlib.Path("some_file.txt")


@dataclasses.dataclass
class BasicConfig:
    foo: int
    full_dt: dt.datetime
    converted_dt: dt.datetime
    filename: pathlib.Path


class Test_BasicTomlConfig(unittest.TestCase):
    def test_ParsesIntField(self):
        cfg = mini_cfg.cfg_from_toml(BASIC_CONFIG_FILE, BasicConfig)

        self.assertEqual(cfg.foo, 10)

    def test_ParsesFullDatetimeField(self):
        cfg = mini_cfg.cfg_from_toml(BASIC_CONFIG_FILE, BasicConfig)

        self.assertEqual(cfg.full_dt, TEST_DATE)

    def test_ConvertsDateToDatetime(self):
        cfg = mini_cfg.cfg_from_toml(BASIC_CONFIG_FILE, BasicConfig)

        self.assertIsInstance(cfg.converted_dt, dt.datetime)

    def test_ConvertedDateIsParsedCorrectly(self):
        cfg = mini_cfg.cfg_from_toml(BASIC_CONFIG_FILE, BasicConfig)

        self.assertEqual(cfg.converted_dt, PARTIAL_DATE)

    def test_PathIsConverted(self):
        cfg = mini_cfg.cfg_from_toml(BASIC_CONFIG_FILE, BasicConfig)

        self.assertEqual(cfg.filename, TEST_PATH)

    def test_DateNotConvertedWhenDisabled(self):
        cfg = mini_cfg.cfg_from_toml(
            BASIC_CONFIG_FILE, BasicConfig, auto_convert_date_to_datetime=False
        )

        self.assertIsInstance(cfg.converted_dt, dt.date)

    def test_DateParsedCorrectlyWhenNotConverted(self):
        cfg = mini_cfg.cfg_from_toml(
            BASIC_CONFIG_FILE, BasicConfig, auto_convert_date_to_datetime=False
        )

        self.assertEqual(cfg.converted_dt, PARTIAL_DATE_AS_DATE)

    def test_PathNotConvertedWhenDisabled(self):
        cfg = mini_cfg.cfg_from_toml(
            BASIC_CONFIG_FILE, BasicConfig, auto_convert_paths=False
        )

        self.assertEqual(cfg.filename, TEST_PATH.name)


NESTED_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/nested_config.toml")
CASCADE_CONFIG_FILE = pathlib.Path("tests/itests/test_configs/cascaded_config.toml")
NESTED_WITH_POINTER_FILE = pathlib.Path(
    "tests/itests/test_configs/nested_with_pointer_config.toml"
)


@dataclasses.dataclass
class NestedConfig(mini_cfg.BaseConfig):
    foo: int
    filename: pathlib.Path


@dataclasses.dataclass
class ConfigWithNest(mini_cfg.BaseConfig):
    nested: NestedConfig


class Test_NestedConfig(unittest.TestCase):
    def test_NestedIntParsed(self):
        cfg = mini_cfg.cfg_from_toml(NESTED_CONFIG_FILE, ConfigWithNest)

        self.assertEqual(cfg.nested.foo, 10)

    def test_NestedPathConverted(self):
        cfg = mini_cfg.cfg_from_toml(NESTED_CONFIG_FILE, ConfigWithNest)

        self.assertIsInstance(cfg.nested.filename, pathlib.Path)

    def test_NestedPathParsedCorrectly(self):
        cfg = mini_cfg.cfg_from_toml(NESTED_CONFIG_FILE, ConfigWithNest)

        self.assertEqual(cfg.nested.filename, TEST_PATH)

    def test_NestedCascadeOverridesVar(self):
        config_files = [NESTED_CONFIG_FILE, CASCADE_CONFIG_FILE]
        cfg = mini_cfg.cfg_from_toml(config_files, ConfigWithNest)

        self.assertEqual(cfg.nested.foo, 999)

    def test_NestedWithPointerParsedCorrectly(self):
        cfg = mini_cfg.cfg_from_toml(NESTED_WITH_POINTER_FILE, ConfigWithNest)

        self.assertEqual(cfg.nested.foo, 10)

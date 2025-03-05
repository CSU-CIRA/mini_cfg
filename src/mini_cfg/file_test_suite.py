"""Provides a test suite to use the same tests among different readers.

Since the same functionality should be tested regardless of file format, this 
module provides parameterized tests that can be reused among multiplte readers.
In order to test a new reader, a set of simple config files should be provided.
The contents of the example toml files should be replicated in your format if
using this test suite to test your reader's functionality:
tests/itests/test_configs/toml/

Basic Config:
    Example: tests/itests/test_configs/toml/basic_config.toml
    This file is used to verify that a simple config file without nesting can
    be parsed. The reader should produce the following dictionary from the file:
    {
        "foo": 10, 
        "full_dt": "2025-02-06 12:05:01", # Can also be a datetime
        "converted_dt": "2025-02-06", # Can also be a date
        "filename": "some_file.txt"
    }   

Nested Config:
    Example: tests/itests/test_configs/toml/nested_config.toml
    This file is used to verify that a config file with a nested sub-config can
    be parsed. The reader should produce the following dictionary from the file:
    {
        "nested":
        {
            "foo": 10,
            "filename": "some_file.txt" 
        }
    }

Cascaded Nested Config:
    Example: tests/itests/test_configs/toml/cascaded_config.toml 
    This file is used to verify that a nested value can be overrided with config
    cascading. This will be used in the cascade: [Nested Config, Cascaded Nested
    Config] to override a value in Nested Config. The reader should produce the
    following dictionary from the file:
    {
        "nested":
        {
            "foo": 999
        }
    }

Nested With Pointer Config:
    Example: tests/itests/test_configs/toml/nested_with_pointer_config.toml 
    This file is used to verify that a config file with a nested sub-config can
    point to a separate config file. This separate file will be parsed as if its
    contents were included in the top-level config file. The reader should
    produce the following dictionary from the file:
    {
        "nested": "path/to/Separated Nested Config"
    }

Separated Nested Config:
    Example: tests/itests/test_configs/toml/separated_nested_config.toml
    This file is used by the Nested With Pointer Config to store the nested
    sub-config data. The reader should produce the following dictionary from the
    file:
    {
        "foo": 10,
        "filename": "some_file.txt"
    }

Nested Cycle A and B Configs:
    Example: tests/itests/test_configs/toml/nested_cycle_a.toml and 
    tests/itests/test_configs/toml/nested_cycle_b.toml
    These files are used to create a cyclic sub-config pointer reference to
    verify that the code will detect the cycle and raise an error. So the "A"
    file will have a sub-config that points to the "B" file.  The "B" file will
    have a sub-config that points back to the "A" file. The reader should
    produce the following dictionaries from the files:
    Nested Cycle A:
    {
        "nested": "path/to/Nested Cycle B"
    }

    Nested Cycle B:
    {
        "nested": "path/to/Nested Cycle A"
    }
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import inspect
import pathlib
import sys
import unittest

from mini_cfg import mini_cfg

TEST_DATE = dt.datetime(2025, 2, 6, 12, 5, 1)
PARTIAL_DATE = dt.datetime(2025, 2, 6)
PARTIAL_DATE_AS_DATE = dt.date(2025, 2, 6)
TEST_PATH = pathlib.Path("some_file.txt")


@dataclasses.dataclass
class TestFixture:
    reader: mini_cfg.FileParserFunc
    tester: unittest.TestCase
    basic_config_file: pathlib.Path
    nested_config_file: pathlib.Path
    cascade_config_file: pathlib.Path
    nested_config_file_with_pointer: pathlib.Path
    nested_config_file_with_cycle_a: pathlib.Path


@dataclasses.dataclass
class BasicConfig:
    foo: int
    full_dt: dt.datetime
    converted_dt: dt.datetime
    filename: pathlib.Path


@dataclasses.dataclass
class NestedConfig(mini_cfg.BaseConfig):
    foo: int
    filename: pathlib.Path


@dataclasses.dataclass
class ConfigWithNest(mini_cfg.BaseConfig):
    nested: NestedConfig


@dataclasses.dataclass
class ConfigWithCycle(mini_cfg.BaseConfig):
    nested: ConfigWithCycle


def perform_tests(fixture: TestFixture) -> None:
    current_module = sys.modules[__name__]
    for m_name, member in inspect.getmembers(current_module):
        if not inspect.isfunction(member):
            continue

        if not m_name.startswith("_test_"):
            continue

        member(fixture)


def _test_basic_ParsesInt(fix: TestFixture) -> None:
    with fix.tester.subTest("Basic parse. Parses Int Field"):
        cfg = mini_cfg.cfg_from_file(fix.basic_config_file, BasicConfig, fix.reader)

        fix.tester.assertEqual(cfg.foo, 10)


def _test_basic_ParsesFullDatetimeField(fix: TestFixture) -> None:
    with fix.tester.subTest("Basic parse. Parses full datetime."):
        cfg = mini_cfg.cfg_from_file(fix.basic_config_file, BasicConfig, fix.reader)

        fix.tester.assertEqual(cfg.full_dt, TEST_DATE)


def _test_basic_DateConvertedToDatetime(fix: TestFixture) -> None:
    with fix.tester.subTest("Basic parse. Converts date to datetime."):
        cfg = mini_cfg.cfg_from_file(fix.basic_config_file, BasicConfig, fix.reader)

        fix.tester.assertIsInstance(cfg.converted_dt, dt.datetime)


def _test_basic_ConvertedDateIsParsedCorrectly(fix: TestFixture) -> None:
    with fix.tester.subTest("Basic parse. Converted date is parsed correctly."):
        cfg = mini_cfg.cfg_from_file(fix.basic_config_file, BasicConfig, fix.reader)

        fix.tester.assertEqual(cfg.converted_dt, PARTIAL_DATE)


def _test_basic_PathIsConverted(fix: TestFixture) -> None:
    with fix.tester.subTest("Basic parse. Path field is converted."):
        cfg = mini_cfg.cfg_from_file(fix.basic_config_file, BasicConfig, fix.reader)

        fix.tester.assertEqual(cfg.filename, TEST_PATH)


def _test_basic_DateNotConvertedWhenDisabled(fix: TestFixture) -> None:
    test_name = "Basic parse. Does not convert date if conversion disabled."
    with fix.tester.subTest(test_name):
        cfg = mini_cfg.cfg_from_file(
            fix.basic_config_file,
            BasicConfig,
            fix.reader,
            convert_dates=False,
        )

        fix.tester.assertIn(type(cfg.converted_dt), [str, dt.date])


def _test_basic_DateParsedCorrectlyWhenNotConverted(fix: TestFixture) -> None:
    test_name = "Basic parse. Date parsed correctly when not converted to datetime."
    with fix.tester.subTest(test_name):
        cfg = mini_cfg.cfg_from_file(
            fix.basic_config_file,
            BasicConfig,
            fix.reader,
            convert_dates=False,
        )

        if isinstance(cfg.converted_dt, dt.date):
            fix.tester.assertEqual(cfg.converted_dt, PARTIAL_DATE_AS_DATE)
        else:
            fix.tester.assertEqual(cfg.converted_dt, "2025-02-06")


def _test_basic_PathNotConvertedWhenDisabled(fix: TestFixture) -> None:
    test_name = "Basic parse. Path not converted when conversion disabled."
    with fix.tester.subTest(test_name):
        cfg = mini_cfg.cfg_from_file(
            fix.basic_config_file, BasicConfig, fix.reader, convert_paths=False
        )

        fix.tester.assertEqual(cfg.filename, TEST_PATH.name)


def _test_nested_IntParsed(fix: TestFixture) -> None:
    with fix.tester.subTest("Nested parse. Nested int field parsed."):
        cfg = mini_cfg.cfg_from_file(fix.nested_config_file, ConfigWithNest, fix.reader)

        fix.tester.assertEqual(cfg.nested.foo, 10)


def _test_nested_PathConverted(fix: TestFixture) -> None:
    with fix.tester.subTest("Nested parse. Nested path field is converted."):
        cfg = mini_cfg.cfg_from_file(fix.nested_config_file, ConfigWithNest, fix.reader)

        fix.tester.assertIsInstance(cfg.nested.filename, pathlib.Path)


def _test_nested_PathParsedCorrectly(fix: TestFixture) -> None:
    with fix.tester.subTest("Nested parse. Nested converted path is parsed correctly."):
        cfg = mini_cfg.cfg_from_file(fix.nested_config_file, ConfigWithNest, fix.reader)

        fix.tester.assertEqual(cfg.nested.filename, TEST_PATH)


def _test_nested_CascadeOverridesVar(fix: TestFixture) -> None:
    test_name = "Nested parse. Config cascade with nesting uses overriden nested value."
    with fix.tester.subTest(test_name):
        config_files = [fix.nested_config_file, fix.cascade_config_file]
        cfg = mini_cfg.cfg_from_file(config_files, ConfigWithNest, fix.reader)

        fix.tester.assertEqual(cfg.nested.foo, 999)


def _test_nested_WithPointerParsedCorrectly(fix: TestFixture) -> None:
    test_name = (
        "Nested parse. Config file with sub-config that points to "
        "separate file is parsed correctly."
    )
    with fix.tester.subTest(test_name):
        cfg = mini_cfg.cfg_from_file(
            fix.nested_config_file_with_pointer, ConfigWithNest, fix.reader
        )

        fix.tester.assertEqual(cfg.nested.foo, 10)


def _test_nested_ValueErrorRaisedWhenCyclicPointerDetected(fix: TestFixture) -> None:
    test_name = (
        "Nested parse. Config file with sub-config (file A) points to "
        "(file B). Nested value in file B points back to file A. "
        "Raises ValueError when this is detected."
    )

    with fix.tester.subTest(test_name):
        with fix.tester.assertRaises(ValueError):
            mini_cfg.cfg_from_file(
                fix.nested_config_file_with_cycle_a, ConfigWithCycle, fix.reader
            )

from __future__ import annotations

import dataclasses
import datetime as dt
import pathlib
import unittest
from typing import Optional

from mini_cfg import mini_cfg

FAKE_PATH = "some_file.txt"


@dataclasses.dataclass
class BasicConfig:
    param_int: int
    path: pathlib.Path
    t_d: dt.datetime
    t_dt: dt.datetime
    t_str: dt.datetime
    t_str_space: dt.datetime


class Test_basic_cfg_from_dict(unittest.TestCase):
    test_dict = {
        "param_int": 10,
        "path": FAKE_PATH,
        "t_d": dt.date(2025, 1, 31),
        "t_dt": dt.datetime(1995, 1, 1),
        "t_str": "2025-02-27 12:15:01",
        "t_str_space": " 2025-02-27 12:15:01  ",
    }

    def test_IntParam(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)
        self.assertEqual(cfg.param_int, 10)

    def test_Pathlib_IsConverted(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)
        expected = pathlib.Path(FAKE_PATH)

        self.assertEqual(cfg.path, expected)

    def test_Date_ConvertedToDatetime(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)

        self.assertIsInstance(cfg.t_d, dt.datetime)

    def test_Date_ConversionIsCorrect(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)

        self.assertEqual(cfg.t_d, dt.datetime(2025, 1, 31))

    def test_Datetime_RemainsDatetime(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)

        self.assertIsInstance(cfg.t_dt, dt.datetime)

    def test_Datetime_IsCorrect(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)

        self.assertEqual(cfg.t_dt, dt.datetime(1995, 1, 1))

    def test_DatetimeStr_ConversionIsCorrect(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)

        self.assertEqual(cfg.t_str, dt.datetime(2025, 2, 27, 12, 15, 1))

    def test_DatetimeStrWithSpace_ConversionIsCorrect(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)

        self.assertEqual(cfg.t_str_space, dt.datetime(2025, 2, 27, 12, 15, 1))


@dataclasses.dataclass
class InheritedSubConfig(mini_cfg.BaseConfig):
    some_int: int


@dataclasses.dataclass
class ConfigWithNestedParams:
    sub: SubConfig
    isub: InheritedSubConfig
    osub: Optional[SubConfig] = None


@dataclasses.dataclass
class SubConfig:
    param_int: int


class Test_nested_cfg_from_dict(unittest.TestCase):
    test_dict = {
        "sub": {"param_int": 10},
        "isub": {"some_int": 100},
        "osub": {"param_int": 111},
    }

    def test_NestedCFG_IsConverted(self) -> None:
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConfigWithNestedParams, sub_classes=[SubConfig]
        )

        self.assertEqual(cfg.sub.param_int, 10)

    def test_InheritedNestedCFG_IsConverted(self) -> None:
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConfigWithNestedParams, sub_classes=[SubConfig]
        )

        self.assertEqual(cfg.isub.some_int, 100)

    def test_OptionalNestedCFG_IsConverted(self) -> None:
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConfigWithNestedParams, sub_classes=[SubConfig]
        )

        self.assertEqual(cfg.osub.param_int, 111)


class Test_recursive_update_dict(unittest.TestCase):
    def test_AddsNewKey(self):
        src = {"a": 10}
        dst = {"b": 100}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertEqual(dst["a"], 10)

    def test_MaintainsOriginalKey(self):
        src = {"a": 10}
        dst = {"b": 100}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertEqual(dst["b"], 100)

    def test_HasExactlyTwoKeys(self):
        src = {"a": 10}
        dst = {"b": 100}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertSequenceEqual(sorted(dst.keys()), ("a", "b"))

    def test_OverridesOverlappingValue(self):
        src = {"a": 10}
        dst = {"a": 100}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertEqual(dst["a"], 10)

    def test_AddsSubValue(self):
        src = {"a": {"foo": 10}}
        dst = {"a": {"bar": 100}}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertEqual(dst["a"]["foo"], 10)

    def test_KeepsSiblingSubValue(self):
        src = {"a": {"foo": 10}}
        dst = {"a": {"bar": 100}}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertEqual(dst["a"]["bar"], 100)

    def test_SubDictHasCorrectKeys(self):
        src = {"a": {"foo": 10}}
        dst = {"a": {"bar": 100}}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertSequenceEqual(sorted(dst["a"].keys()), ("bar", "foo"))

    def test_SubDictOverridesOverlappingValue(self):
        src = {"a": {"foo": 10}}
        dst = {"a": {"foo": 100}}

        mini_cfg.recursive_update_dict(src, dst)
        self.assertEqual(dst["a"]["foo"], 10)


class CustomDataType:
    def __init__(self, value: str):
        self.val = int(value)


class FromFunc:
    def __init__(self, value: str):
        self.val = int(value)


def convert_func(value: str) -> FromFunc:
    return FromFunc(value)


@dataclasses.dataclass
class ConvConfig:
    cust: CustomDataType
    from_func: FromFunc
    sub: SubConvConfig
    opt_cust: Optional[CustomDataType] = None
    none_opt_cust: Optional[CustomDataType] = None
    opt_from_func: Optional[FromFunc] = None
    none_opt_from_func: Optional[FromFunc] = None


@dataclasses.dataclass
class SubConvConfig(mini_cfg.BaseConfig):
    sub_cust: CustomDataType


class Test_custom_conversion(unittest.TestCase):
    test_dict = {
        "cust": "10",
        "opt_cust": "100",
        "from_func": "999",
        "opt_from_func": "-999",
        "sub": {"sub_cust": "777"},
    }
    converters = {CustomDataType: CustomDataType, FromFunc: convert_func}

    def test_CustomDataType_IsConverted(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertEqual(cfg.cust.val, 10)

    def test_OptionalCustomDataType_IsConverted(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertEqual(cfg.opt_cust.val, 100)

    def test_OptionalCustomDataTypeSetToNone_IsNone(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertIsNone(cfg.none_opt_cust)

    def test_FromFunc_ConvertedUsingFunc(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertEqual(cfg.from_func.val, 999)

    def test_OptionalFromFunc_IsConverted(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertEqual(cfg.opt_from_func.val, -999)

    def test_OptionalFromFuncSetToNone_IsNone(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertIsNone(cfg.none_opt_from_func)

    def test_SubCustomDataType_IsConverted(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, ConvConfig, converters=self.converters
        )

        self.assertEqual(cfg.sub.sub_cust.val, 777)


@dataclasses.dataclass
class DisablePathlibConv:
    p: pathlib.Path


class Test_disable_pathlib_conversion(unittest.TestCase):
    test_dict = {"p": FAKE_PATH}

    def test_IsNotConvertedToPath(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, DisablePathlibConv, auto_convert_paths=False
        )

        self.assertNotIsInstance(cfg.p, pathlib.Path)

    def test_HasOriginalString(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, DisablePathlibConv, auto_convert_paths=False
        )

        self.assertEqual(cfg.p, FAKE_PATH)


@dataclasses.dataclass
class DisableDateConv:
    d: dt.datetime


class Test_disable_date_conversion(unittest.TestCase):
    test_dict = {"d": dt.date(2024, 10, 1)}

    def test_IsNotConvertedToDatetime(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, DisableDateConv, auto_convert_date_to_datetime=False
        )

        self.assertNotIsInstance(cfg.d, dt.datetime)

    def test_RemainsDate(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, DisableDateConv, auto_convert_date_to_datetime=False
        )

        self.assertIsInstance(cfg.d, dt.date)

    def test_HasOriginalDate(self):
        cfg = mini_cfg.cfg_from_dict(
            self.test_dict, DisableDateConv, auto_convert_date_to_datetime=False
        )

        self.assertEqual(cfg.d, dt.date(2024, 10, 1))


@dataclasses.dataclass
class ValidationMock:
    reached: bool = False


@dataclasses.dataclass
class ValidateSubLevel(mini_cfg.BaseConfig):
    bar: ValidationMock

    def _do_validation(self):
        self.bar.reached = True


@dataclasses.dataclass
class ValidateTopLevel(mini_cfg.BaseConfig):
    foo: ValidationMock
    sub_config: ValidateSubLevel

    def _do_validation(self):
        self.foo.reached = True


class Test_Validation(unittest.TestCase):
    def _get_test_config(self):
        d = {"foo": ValidationMock(), "sub_config": {"bar": ValidationMock()}}
        return mini_cfg.cfg_from_dict(d, ValidateTopLevel)

    def test_TopLevelValidationReached(self) -> None:
        cfg = self._get_test_config()
        cfg.validate()
        self.assertTrue(cfg.foo.reached)

    def test_SubLevelValidationReached(self) -> None:
        cfg = self._get_test_config()
        cfg.validate()
        self.assertTrue(cfg.sub_config.bar.reached)

    def test_ValidationNotCalled_TopLevelValidationNotReached(self) -> None:
        cfg = self._get_test_config()
        self.assertFalse(cfg.foo.reached)

    def test_ValidationNotCalled_SubLevelValidationNotReached(self) -> None:
        cfg = self._get_test_config()
        self.assertFalse(cfg.sub_config.bar.reached)

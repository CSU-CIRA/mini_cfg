from __future__ import annotations

import dataclasses
import pathlib
import unittest
from typing import Optional

from mini_cfg import mini_cfg

FAKE_PATH = "some_file.txt"


@dataclasses.dataclass
class BasicConfig:
    param_int: int
    path: pathlib.Path


class Test_basic_cfg_from_dict(unittest.TestCase):
    test_dict = {"param_int": 10, "path": FAKE_PATH}

    def test_IntParam(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)
        self.assertEqual(cfg.param_int, 10)

    def test_Pathlib_IsConverted(self):
        cfg = mini_cfg.cfg_from_dict(self.test_dict, BasicConfig)
        expected = pathlib.Path(FAKE_PATH)

        self.assertEqual(cfg.path, expected)


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

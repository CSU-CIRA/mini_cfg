import dataclasses
import datetime as dt
import inspect
import pathlib
import tomllib
from typing import Any, Dict, Type, TypeVar

T = TypeVar("T")


@dataclasses.dataclass
class BaseConfig:
    pass


def cfg_from_toml(path: pathlib.Path, config_class: T) -> Type[T]:
    with open(path, "rb") as in_file:
        toml_dict = tomllib.load(in_file)

    return cfg_from_dict(toml_dict, config_class)


def cfg_from_dict(d: Dict[str, Any], config_class: T) -> Type[T]:
    instance = config_class(**d)

    an = inspect.get_annotations(instance)
    pass

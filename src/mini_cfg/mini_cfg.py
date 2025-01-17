import dataclasses
import datetime as dt
import inspect
import pathlib
import tomllib
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")


@dataclasses.dataclass
class BaseConfig:
    pass


def cfg_from_toml(path: pathlib.Path, config_class: T) -> Type[T]:
    with open(path, "rb") as in_file:
        toml_dict = tomllib.load(in_file)

    return cfg_from_dict(toml_dict, config_class)


def cfg_from_dict(
    d: Dict[str, Any], config_class: T, sub_classes: Optional[List[T]] = None
) -> Type[T]:
    instance = config_class(**d)
    _convert_sub_classes(instance, config_class, sub_classes)

    return instance


def _convert_sub_classes(
    instance: T, config_class: T, sub_classes: Optional[List[T]] = None
) -> None:
    if sub_classes is None:
        sub_classes = []

    annotations = inspect.get_annotations(config_class, eval_str=True)
    for attr, attr_type in annotations.items():
        if _is_attr_sub_class(attr_type, sub_classes):
            given_value = instance.__dict__[attr]
            if isinstance(given_value, dict):
                instance.__dict__[attr] = cfg_from_dict(given_value, attr_type)


def _is_attr_sub_class(attr_type: Type, sub_classes: List[T]) -> bool:
    if attr_type in sub_classes:
        return True

    if inspect.isclass(attr_type) and issubclass(attr_type, BaseConfig):
        return True

    return False

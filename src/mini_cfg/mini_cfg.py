import dataclasses
import datetime as dt
import inspect
import json
import pathlib
import tomllib
import types
import typing
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")
FileParserFunc = Callable[[pathlib.Path, T, Optional[List[T]]], T]

NONE_TYPE = type(None)


@dataclasses.dataclass
class BaseConfig:
    pass


def cfg_from_toml(
    path: pathlib.Path, config_class: T, sub_classes: Optional[List[T]] = None
) -> Type[T]:
    with open(path, "rb") as in_file:
        toml_dict = tomllib.load(in_file)

    return cfg_from_dict(toml_dict, config_class, sub_classes, cfg_from_toml)


def cfg_from_json(
    path: pathlib.Path, config_class: T, sub_classes: Optional[List[T]] = None
) -> Type[T]:
    with open(path, "r") as in_file:
        json_dict = json.load(in_file)

    return cfg_from_dict(json_dict, config_class, sub_classes, cfg_from_json)


def cfg_from_yaml(
    path: pathlib.Path, config_class: T, sub_classes: Optional[List[T]] = None
) -> Type[T]:
    import yaml

    with open(path, "r") as in_file:
        yaml_dict = yaml.safe_load(in_file)

    return cfg_from_dict(yaml_dict, config_class, sub_classes, cfg_from_yaml)


def cfg_from_dict(
    d: Dict[str, Any],
    config_class: T,
    sub_classes: Optional[List[T]] = None,
    parser_func: Optional[FileParserFunc] = None,
) -> Type[T]:
    instance = config_class(**d)
    _convert_sub_classes(instance, config_class, sub_classes, parser_func)

    return instance


def _convert_sub_classes(
    instance: T,
    config_class: T,
    sub_classes: Optional[List[T]] = None,
    parser_func: Optional[FileParserFunc] = None,
) -> None:
    if sub_classes is None:
        sub_classes = []

    hints = typing.get_type_hints(config_class)
    for attr, raw_hint in hints.items():
        hint_type = _normalize_hint(raw_hint)
        if _is_attr_sub_class(hint_type, sub_classes):
            given_value = instance.__dict__[attr]

            if _is_hint_optional(raw_hint) and given_value is None:
                continue

            if isinstance(given_value, dict):
                instance.__dict__[attr] = cfg_from_dict(given_value, hint_type)

            if isinstance(given_value, str):
                sub_file_path = pathlib.Path(given_value)
                instance.__dict__[attr] = parser_func(
                    sub_file_path, config_class, sub_classes
                )


def _is_attr_sub_class(attr_type: Type, sub_classes: List[T]) -> bool:

    if attr_type in sub_classes:
        return True

    if inspect.isclass(attr_type) and issubclass(attr_type, BaseConfig):
        return True

    return False


def _is_hint_optional(attr_type: Type) -> bool:
    args = typing.get_args(attr_type)
    if len(args) != 2:
        return False

    if args.count(types.NoneType) != 1:
        return False

    if inspect.isclass(args[0]) or inspect.isclass(args[1]):
        return True

    return False


def _unpack_optional(hint: Type) -> Type:
    args = typing.get_args(hint)
    if args[0] != types.NoneType:
        return args[0]

    if args[1] != types.NoneType:
        return args[1]

    raise ValueError("Can not unpack non Optional type hint.")


def _normalize_hint(hint: Type) -> Type:
    if _is_hint_optional(hint):
        return _unpack_optional(hint)

    return hint

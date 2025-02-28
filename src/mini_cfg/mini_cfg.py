import dataclasses
import datetime as dt
import inspect
import logging
import pathlib
import tomllib
import types
import typing
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

T = TypeVar("T")
FileParserFunc = Callable[[pathlib.Path], Dict[str, Any]]

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


NONE_TYPE = type(None)


@dataclasses.dataclass
class BaseConfig:
    def validate(self) -> None:
        self._do_validation()

        for value in self.__dict__.values():
            if isinstance(value, BaseConfig):
                value.validate()

    def _do_validation(self) -> None:
        pass


def cfg_from_file(
    paths: pathlib.Path | List[pathlib.Path],
    config_class: T,
    reader: FileParserFunc,
    sub_classes: Optional[List[T]] = None,
    converters: Optional[Dict[T, Callable]] = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
    parent_files: Optional[List[pathlib.Path]] = None,
) -> Type[T]:
    """Creates a config from a file cascade using a provided reader callable."""
    try:
        paths = _convert_single_path_to_list(paths)
        _check_for_cycle(paths, parent_files)
        final_dict = _eval_cascade(paths, reader)
        file_history = _create_file_history(paths, parent_files)

        return cfg_from_dict(
            final_dict,
            config_class,
            sub_classes,
            reader,
            converters,
            convert_paths,
            convert_dates,
            file_history,
        )
    except Exception as ex:
        _add_note(ex, paths, config_class)
        raise


def _convert_single_path_to_list(
    paths: pathlib.Path | List[pathlib.Path],
) -> List[pathlib.Path]:
    if isinstance(paths, pathlib.Path):
        return [paths]

    return paths


def _eval_cascade(paths: pathlib.Path, reader: FileParserFunc) -> Dict[str, Any]:
    final_dict = {}
    for path in paths:
        read_dict = reader(path)

        recursive_update_dict(read_dict, final_dict)
    return final_dict


def _add_note(ex: Exception, paths: List[pathlib.Path], config_class: T) -> None:
    str_paths = [str(p) for p in paths]
    msg = f"Error creating config type: {config_class} from cascade: {str_paths}"
    ex.add_note(msg)


def _create_file_history(
    paths: List[pathlib.Path], parent_files: Optional[List[pathlib.Path]] = None
) -> List[pathlib.Path]:
    file_history = []
    if parent_files is not None:
        file_history.extend(parent_files)
    file_history.extend(paths)
    return file_history


def _check_for_cycle(
    paths: List[pathlib.Path], parent_paths: Optional[List[pathlib.Path]] = None
) -> None:
    if parent_paths is None:
        return

    for p in paths:
        if p in parent_paths:
            msg = (
                f"Cyclic file reference detected while attempting to "
                f"create sub-config from previously visited file: {p}. "
                f"File history: {parent_paths}."
            )
            raise ValueError(msg)


def recursive_update_dict(src_dict: Dict[str, Any], dst_dict: Dict[str, Any]):
    for k, v in src_dict.items():
        if _val_is_dict(v):
            if k not in dst_dict:
                dst_dict[k] = {}

            recursive_update_dict(v, dst_dict[k])
        else:
            dst_dict[k] = v


def _val_is_dict(val: Any) -> bool:
    try:
        val.items()
    except AttributeError:
        return False

    return True


def _read_toml(path: pathlib.Path) -> Dict[str, Any]:
    with open(path, "rb") as in_file:
        return tomllib.load(in_file)


def _read_yaml(path: pathlib.Path) -> Dict[str, Any]:
    import yaml

    with open(path, "r") as in_file:
        return yaml.safe_load(in_file)


def cfg_from_toml(
    paths: pathlib.Path | List[pathlib.Path],
    config_class: T,
    sub_classes: Optional[List[T]] = None,
    converters: Optional[Dict[T, Callable]] = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
) -> Type[T]:
    """Creates a config from a TOML file cascade."""
    return cfg_from_file(
        paths,
        config_class,
        _read_toml,
        sub_classes,
        converters,
        convert_paths,
        convert_dates,
    )


def cfg_from_yaml(
    paths: pathlib.Path | List[pathlib.Path],
    config_class: T,
    sub_classes: Optional[List[T]] = None,
    converters: Optional[Dict[T, Callable]] = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
) -> Type[T]:
    """Creates a config from a YAML file cascade."""
    return cfg_from_file(
        paths,
        config_class,
        _read_yaml,
        sub_classes,
        converters,
        convert_paths,
        convert_dates,
    )


def cfg_from_dict(
    d: Dict[str, Any],
    config_class: T,
    sub_classes: Optional[List[T]] = None,
    parser_func: Optional[FileParserFunc] = None,
    converters: Optional[Dict[T, Callable]] = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
    parent_files: Optional[List[pathlib.Path]] = None,
) -> Type[T]:
    instance = config_class(**d)

    if converters is None:
        converters = {}
    else:
        # Avoid side effect of adding things to the converters by making a
        # shallow copy.
        converters = dict(converters)

    if pathlib.Path not in converters and convert_paths:
        converters[pathlib.Path] = pathlib.Path

    if dt.datetime not in converters and convert_dates:
        converters[dt.datetime] = _convert_date

    _convert_sub_classes(
        instance,
        config_class,
        sub_classes,
        parser_func,
        converters,
        convert_paths,
        convert_dates,
        parent_files,
    )
    _custom_conversions(instance, config_class, converters)
    return instance


def _convert_sub_classes(
    instance: T,
    config_class: T,
    sub_classes: Optional[List[T]] = None,
    parser_func: Optional[FileParserFunc] = None,
    converters: Optional[Dict[T, Callable]] = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
    parent_files: Optional[List[pathlib.Path]] = None,
) -> None:
    """Iterates over attributes of instance and converts sub-classes it finds.

    Each attribute that has a type hint that is either in the sub_classes list,
    or is a child class of BaseConfig will have its value converted to an instance
    of the type hint's class.  The value of the attribute must be a dictionary,
    or a string that is assumed to be a path to another config file. If the
    value of the attribute is already an instance of the type hint's class, then
    the attribute will be skipped.  Otherwise, a TypeError will be thrown. If an
    attribute is Optional and set to None, then conversion will be skipped.
    """
    if sub_classes is None:
        sub_classes = []

    hints = typing.get_type_hints(config_class)
    for attr_name, raw_hint in hints.items():
        hint_type = _normalize_hint(raw_hint)
        if not _is_attr_sub_class(hint_type, sub_classes):
            continue

        given_value = instance.__dict__[attr_name]

        if _is_optional_hint_set_to_none(raw_hint, given_value):
            continue

        if _is_value_already_correct_type(given_value, hint_type):
            continue

        if isinstance(given_value, dict):
            instance.__dict__[attr_name] = cfg_from_dict(
                given_value,
                hint_type,
                sub_classes,
                parser_func,
                converters,
                convert_paths,
                convert_dates,
                parent_files,
            )
        elif isinstance(given_value, str):
            sub_file_path = pathlib.Path(given_value)
            instance.__dict__[attr_name] = cfg_from_file(
                sub_file_path,
                hint_type,
                parser_func,
                sub_classes,
                converters,
                convert_paths,
                convert_dates,
                parent_files,
            )
        else:
            _raise_type_error(attr_name, hint_type, given_value)


def _raise_type_error(attr: str, hint_type: Type, given_value: Any) -> None:
    given_type = type(given_value)
    msg = f"Can't convert {attr} to {hint_type} if value is not a dict or str. Given: {given_type}"
    raise TypeError(msg)


def _is_optional_hint_set_to_none(hint: Type, given_value: Any) -> bool:
    return _is_hint_optional(hint) and given_value is None


def _is_value_already_correct_type(given_value: Any, t: Type) -> bool:
    return isinstance(given_value, t)


def _is_attr_sub_class(attr_type: Type, sub_classes: List[T]) -> bool:

    if attr_type in sub_classes:
        return True

    if _is_attr_base_config(attr_type):
        return True

    return False


def _is_attr_base_config(attr_type: Type) -> bool:
    return inspect.isclass(attr_type) and issubclass(attr_type, BaseConfig)


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


def _custom_conversions(
    instance: T, config_class: T, converters: Dict[T, Callable]
) -> None:
    """Iterates over attributes of instance and performs custom conversions."""
    hints = typing.get_type_hints(config_class)
    for attr, raw_hint in hints.items():
        hint_type = _normalize_hint(raw_hint)

        if hint_type not in converters:
            continue

        given_value = instance.__dict__[attr]

        if _is_hint_optional(raw_hint) and given_value is None:
            continue

        converter = converters[hint_type]
        instance.__dict__[attr] = converter(given_value)


def _convert_date(d: dt.date | dt.datetime | str) -> dt.datetime:
    """Converts date, and ISO-8601 strings to datetime."""
    if isinstance(d, dt.datetime):
        return d

    if isinstance(d, str):
        return dt.datetime.fromisoformat(d.strip())

    return dt.datetime(d.year, d.month, d.day)

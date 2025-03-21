"""Provides all of mini_cfg functionality."""

import dataclasses
import datetime as dt
import inspect
import logging
import pathlib
import tomllib
import types
import typing
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

# This represents a generic class passed in by the user.
T = TypeVar("T")
# Optional list of passed classes that config sub-dictionaries will be converted to.
SubClassList = Optional[List[Type[T]]]
# Optional dictionary mapping classes to a Callable that will convert config
# dictionary values to an instance of the class.
ConverterDict = Optional[Dict[Type[T], Callable]]
# Callable that will take a file path and, presumably, read the file at the path
# to produce a dictionary.
FileParserFunc = Callable[[pathlib.Path], Dict[str, Any]]

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


NONE_TYPE = type(None)


@dataclasses.dataclass
class BaseConfig:
    """Config base class.

    Any dataclass that inherits from this class can be used as a
    sub-configuration object. After the config file has been read an instance of
    the higher level configuration object has been constructed, the type hint of
    each attribute will be inspected.  If the type hint inherits from
    BaseConfig, then the value of the attribute will be converted to class in
    the type hint.

    This class also provides a simple mechanism for performing validation via
    the validate and _do_validation methods.
    """

    def validate(self) -> None:
        """Recursively performs validation.

        If the validate method is called on an instance, it will call
        _do_validation on itself and then recursively call validate on any
        attributes that inherit from BaseConfig. The _do_validation method can
        be implemented in child classes to actually perform validation.
        """
        self._do_validation()

        for value in self.__dict__.values():
            if isinstance(value, BaseConfig):
                value.validate()

    def _do_validation(self) -> None:
        """Abstract method to perform validation.

        This method should be implemented by child classes to perform validation.
        """


def cfg_from_file(
    paths: pathlib.Path | List[pathlib.Path],
    config_class: Type[T],
    reader: FileParserFunc,
    sub_classes: SubClassList = None,
    converters: ConverterDict = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
    parent_files: Optional[List[pathlib.Path]] = None,
) -> T:
    """Creates a config from a file cascade using a provided reader callable.

    Generic config construction function that assumes that a reader is provided
    that will read dictionaries from given files.  The cfg_from_toml and
    cfg_from_yaml functions are basically wrappers around this function that
    pass the toml/yaml reading code.

    This takes any files that have been passed and performs a recursive
    dictionary merge to collapse the dictionaries from the read files into a
    single dictionary.

    When file pointers are used, this function may have been called recursively.
    The code keeps track of which files were visited to reach this call of the
    function. This history is checked to make sure that files are not visited
    more than once to ensure a cycle is not generated by the file pointers. If
    a cycle is detected, the function throws a ValueError.

    The code also intercepts any errors that occured at a lower level and adds
    information about which files were previously parsed to assist with debugging.

    Args:
        paths (pathlib.Path | List[pathlib.Path]): Config filename or list of
            filenames making a cascade.
        config_class (Type[T]): The class to convert the cascade to.
        reader (FileParserFunc): Reader function that takes a filename and
            returns a dictionary.
        sub_classes (SubClassList, optional): List of classes that can be
            converted to sub-config objects. Defaults to None.
        converters (ConverterDict, optional): Dictionary mapping
            classes that may appear as attribute type hints on the config_class
            and the Callable that will convert whatever the value of the
            attribute is to an instance of the type hint class. Defaults to
            None.
        convert_paths (bool, optional): Whether or not to automatically convert
            attributes on the config_class with a type hint of pathlib.Path from
            string to path. Defaults to True.
        convert_dates (bool, optional): Whether or not to automatically convert
            attributes on the config_class with a type hint of datetime from
            date/datetime/str to datetime. Defaults to True.
        parent_files (Optional[List[pathlib.Path]], optional): List of
            files previously used to recursively construct the config object and
            its sub-classes.  Will be checked for cycles. Defaults to None.

    Raises:
        TypeError: If a sub-config is detected in a config_class attribute
            type hint, but the value of the attribute can not be converted.
            The values in a sub-config attribute must either be a dictionary
            or a string that is assumed to be a path.
        ValueError: If a cycle is detected between the config cascade and the
            parent_files.

    Returns:
        T: A instance of config_class constructed from the given config
            cascase.
    """
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


def _eval_cascade(paths: List[pathlib.Path], reader: FileParserFunc) -> Dict[str, Any]:
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


def recursive_update_dict(src_dict: Dict[str, Any], dst_dict: Dict[str, Any]) -> None:
    """Recursively adds/overwrites contents of src_dict into dst_dict.

    Performs merge as a side effect, so the contents of dst_dict will be altered.

    Any keys/values not in dst_dict that are in src_dict will end up in
    dst_dict. If both src_dict and dst_dict have the same keys, then src_dict
    will overwrite the value in dst_dict.  This is performed recursively on
    dictionaries found in src_dict.

    Args:
        src_dict (Dict[str, Any]): The dictionary whose contents will populate
            dst_dict.
        dst_dict (Dict[str, Any]): The dictionary whose contents will be
            populated by src_dict.
    """
    for k, v in src_dict.items():
        if _val_is_dict(v):
            if k not in dst_dict:
                dst_dict[k] = {}

            if not _val_is_dict(dst_dict[k]):
                dst_dict[k] = v
                continue

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
    try:
        import yaml
    except ImportError as ex:
        msg = (
            "pyyaml needed to use YAML config files. "
            "Install with optional dependency: pip install mini_cfg[read_yaml]"
        )
        ex.add_note(msg)
        raise

    with open(path, "r") as in_file:
        return yaml.safe_load(in_file)


def cfg_from_toml(
    paths: pathlib.Path | List[pathlib.Path],
    config_class: Type[T],
    sub_classes: SubClassList = None,
    converters: ConverterDict = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
) -> T:
    """Creates a config from a TOML file cascade.

    Wrapper for passing _read_toml to cfg_from_file.

    Args:
        paths (pathlib.Path | List[pathlib.Path]): Config filename or list of
            filenames making a cascade.
        config_class (Type[T]): The class to convert the cascade to.
        sub_classes (SubClassList, optional): List of classes that can be
            converted to sub-config objects.
        converters (ConverterDict, optional): Dictionary mapping
            classes that may appear as attribute type hints on the config_class
            and the Callable that will convert whatever the value of the
            attribute is to an instance of the type hint class. Defaults to
            None.
        convert_paths (bool, optional): Whether or not to automatically convert
            pathlib.Path attributes from strings to paths. Defaults to True.
        convert_dates (bool, optional): Whether or not to automatically convert
            datetime attributes from date/datetime/str to datetime. Defaults to
            True.

    Raises:
        TypeError: If a sub-config is detected in a config_class attribute
            type hint, but the value of the attribute can not be converted.
            The values in a sub-config attribute must either be a dictionary
            or a string that is assumed to be a path.
        ValueError: If a cycle is detected when file pointers are used in the
            given config files.

    Returns:
        T: A instance of config_class constructed from the given config
            cascade.
    """
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
    config_class: Type[T],
    sub_classes: SubClassList = None,
    converters: ConverterDict = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
) -> T:
    """Creates a config from a YAML file cascade.

    Wrapper for passing _read_yaml to cfg_from_file.

    Args:
        paths (pathlib.Path | List[pathlib.Path]): Config filename or list of
            filenames making a cascade.
        config_class (T): The class to convert the cascade to.
        sub_classes (SubClassList, optional): List of classes that can be
            converted to sub-config objects.
        converters (ConverterDict, optional): Dictionary mapping
            classes that may appear as attribute type hints on the config_class
            and the Callable that will convert whatever the value of the
            attribute is to an instance of the type hint class. Defaults to
            None.
        convert_paths (bool, optional): Whether or not to automatically convert
            pathlib.Path attributes from strings to paths. Defaults to True.
        convert_dates (bool, optional): Whether or not to automatically convert
            datetime attributes from date/datetime/str to datetime. Defaults to
            True.

    Raises:
        ImportError: If pyyaml is not installed in your environment.
        TypeError: If a sub-config is detected in a config_class attribute
            type hint, but the value of the attribute can not be converted.
            The values in a sub-config attribute must either be a dictionary
            or a string that is assumed to be a path.
        ValueError: If a cycle is detected when file pointers are used in the
            given config files.

    Returns:
        T: A instance of config_class constructed from the given config
            cascade.
    """
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
    config_class: Type[T],
    sub_classes: SubClassList = None,
    reader: Optional[FileParserFunc] = None,
    converters: ConverterDict = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
    parent_files: Optional[List[pathlib.Path]] = None,
) -> T:
    """Converts dictionary to given config class.

    After reading has been performed inside cfg_from_file, this function is
    called to actually perform the conversion from the read dictionary to the
    config_class.

    Args:
        d (Dict[str, Any]): Dictionary to convert.
        config_class (Type[T]): The class to convert the dictionary to.
        sub_classes (SubClassList, optional): List of classes that can be
            converted to sub-config objects. Defaults to None.
        reader (Optional[FileParserFunc], optional): Reader function that takes
            a filename and returns a dictionary. This will not be used directly
            by this function, but it will be used if file pointers are
            encountered in the config file. Defaults to None.
        converters (ConverterDict, optional): Dictionary mapping
            classes that may appear as attribute type hints on the config_class
            and the Callable that will convert whatever the value of the
            attribute is to an instance of the type hint class. Defaults to
            None.
        convert_paths (bool, optional): Whether or not to automatically convert
            attributes on the config_class with a type hint of pathlib.Path from
            string to path. Defaults to True.
        convert_dates (bool, optional): Whether or not to automatically convert
            attributes on the config_class with a type hint of datetime from
            date/datetime/str to datetime. Defaults to True.
        parent_files (Optional[List[pathlib.Path]], optional): List of
            files previously used to recursively construct the config object and
            its sub-classes.  Will be checked for cycles. Defaults to None.

    Raises:
        TypeError: If a sub-config is detected in a config_class attribute
            type hint, but the value of the attribute can not be converted.
            The values in a sub-config attribute must either be a dictionary
            or a string that is assumed to be a path.
        ValueError: If file pointers are encountered and a cycle is detected.

    Returns:
        T: A instance of config_class constructed from the given
            dictionary.
    """
    instance = config_class(**d)

    converters = _add_auto_converters(converters, convert_paths, convert_dates)

    _convert_sub_classes(
        instance,
        config_class,
        sub_classes,
        reader,
        converters,
        convert_paths,
        convert_dates,
        parent_files,
    )
    _custom_conversions(instance, config_class, converters)
    return instance


def _add_auto_converters(
    converters: Optional[Dict[Type[T], Callable]] = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
) -> Dict[T, Callable]:
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

    return converters


def _convert_sub_classes(
    instance: T,
    config_class: Type[T],
    sub_classes: SubClassList = None,
    parser_func: Optional[FileParserFunc] = None,
    converters: ConverterDict = None,
    convert_paths: bool = True,
    convert_dates: bool = True,
    parent_files: Optional[List[pathlib.Path]] = None,
) -> None:
    """Iterates over attributes of instance and converts sub-classes it finds.

    Each attribute that has a type hint that is either in the sub_classes list,
    or is a child class of BaseConfig will have its value converted to an
    instance of the type hint's class. The value of the attribute must be a
    dictionary, or a string that is assumed to be a path to another config file.
    If the value of the attribute is already an instance of the type hint's
    class, then the attribute will be skipped. Otherwise, a TypeError will be
    thrown. If an attribute is Optional and set to None, then conversion will be
    skipped.
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
    instance: T, config_class: Type[T], converters: Dict[Type[T], Callable]
) -> None:
    """Iterates over attributes of instance and performs custom conversions.

    Each attribute of the instance has its type hint checked. If the class
    of the type hint is a key in converters, then the value of the attribute
    will be passed to the Callable associated with it to perform conversion.
    """
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
    """Converts date/datetime, and ISO-8601 strings to datetime."""
    if isinstance(d, dt.datetime):
        return d

    if isinstance(d, str):
        return dt.datetime.fromisoformat(d.strip())

    return dt.datetime(d.year, d.month, d.day)

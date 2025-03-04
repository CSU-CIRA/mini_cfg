# mini_cfg
A minimal, no dependency, library that assists with storing configuration 
information in dataclasses and makes no assumptions about the high level 
structure of your code.

It is almost always desirable to move parameters for executable code into a 
configuration file. This is easy to achieve using a `dataclass` and Python's 
buit-in TOML reader:
```python
import dataclasses
import tomllib

@dataclasses.dataclass
class Config:
    a: int
    b: float

def read_config(filename: pathlib.Path) -> Config:
    with open(filename, "rb") as f:
        data = tomllib.load(f)
        return Config(**data)

def main():
    config = read_config("config_file.toml")
    print("a:", config.a)
    print("b:", config.b)
```

For simple applications, the above code is usually sufficient.  However, in
more advanced applications, code starts accumulating to handle the configuration 
files/data. This library was written to reduce the amount of boilerplate code
that needs to be written to handle common "advanced" configuration use cases.  

At the moment only TOML and YAML files are supported.  If TOML files are used, 
then this library will have no dependencies.  If YAML files are used then the 
`pyyaml` library should be installed.  However, the library makes it extremely 
easy to parse configuration from other formats.

## Usage

### Basics
To read a simple TOML configuration file into a dataclass, the `cfg_from_toml`
function can be used.  You simply provide it the config filename and the class
that should be constructed:
Example TOML file:
```TOML
foo = 10
```

Python to read the TOML file into a `dataclass`.
```python
import dataclasses
import pathlib

from mini_cfg import mini_cfg

CFG_FILE = pathlib.Path("example.toml")

@dataclasses.dataclass
class Config:
    foo:int

config = mini_cfg.cfg_from_toml(CFG_FILE, Config)
print(config.foo)
``` 

If a YAML file is used instead of a TOML file, then `cfg_from_yaml` can be used
instead of `cfg_from_toml`.

If you have a dictionary rather than a file, then `cfg_from_dict` can be used to
instantiate the `dataclass` from the dictionary:
```python
config_dict = {"foo":10}
config = mini_cfg.cfg_from_dict(config_dict, Config)
```

### Automatic pathlib/datetime Conversion

#### pathlib.Path Conversions
It is usually preferable to represent paths using `pathlib.Path` objects rather
than storing them as strings.  However, TOML/YAML parsers do not automatically 
produces `pathlib.Path` objects. Converting strings to paths can produce a lot
of boilerplate code.  By default, any attribute of your `dataclass` whose type
hint is `pathlib.Path` will have its value be converted from `str` to 
`pathlib.Path`.  To disable this behaviour, you can pass `convert_paths=False`
to `cfg_from_toml`/`cfg_from_yaml`/`cfg_from_dict`.
Example:
```toml
some_file = "path/to/file.txt"
``` 
```python
@dataclasses.dataclass
class Config:
    some_file: pathlib.Path

config_file = pathlib.Path("example_config.toml")

config = mini_cfg.cfg_from_toml(config_file, Config)
config_conversion_disabled = mini_cfg.cfg_from_toml(
    config_file, Config, convert_paths=False)

print(config.some_file, " ", type(config.some_file))
print(config.some_file, " ", type(config_conversion_disabled.some_file))
```    

This will produce the output:
```bash
path/to/file.txt   <class 'pathlib.PosixPath'>
path/to/file.txt   <class 'str'>
```

#### Datetime Conversions
When given a full ISO-8601 time, `pyyaml` and `tomllib` will produce a `datetime`
object.  However, when they are given just an ISO-8601 year, month, and day they
will produce a `date` object instead.  This can cause a problem if downstream
code assumes that hours, minutes, seconds, etc. are always available in the 
objects they are given.  Additionally a dictionary obtained outside of a YAML or
TOML file may represent times as strings.  By default, any attribute of your 
`dataclass` whose type hint is `datetime` will have its value be converted to
`datetime`.  To disable this behaviour, you can pass `convert_dates=False`
to `cfg_from_toml`/`cfg_from_yaml`/`cfg_from_dict`.  The actual value of the 
attribute prior to conversion may be a `datetime` object, a `date` object, or
a string representing an ISO-8601 compatible date.
Example:
```toml
foo = 2025-02-28
```
```python
import datetime as dt

@dataclasses.dataclass
class Config:
    foo: dt.datetime


config_file = pathlib.Path("example_config.toml")

config = mini_cfg.cfg_from_toml(config_file, Config)
config_no_date_conversion = mini_cfg.cfg_from_toml(
    config_file, Config, convert_dates=False)

config_dict = {"foo":"2025-02-28"}
config_date_from_str = mini_cfg.cfg_from_dict(config_dict, Config)

# Will be a datetime object even though only year, month, day is provided
print(config.foo, " ", type(config.foo))
# Will be a date object since conversion was disabled
print(config_no_date_conversion.foo, " ", type(config_no_date_conversion.foo))
# Will be a datetime object parsed from the string in the dict
print(config_date_from_str.foo, " ", type(config_date_from_str.foo))
```

This produces the output:
```bash
2025-02-28 00:00:00   <class 'datetime.datetime'>
2025-02-28   <class 'datetime.date'>
2025-02-28 00:00:00   <class 'datetime.datetime'>
```

### Hierarchical Configuration
Although it is possible to have a flat configuration where all the parameters are
part of a single large configuration object, it is usually beneficial to split 
parameters into sections by sub-system.  Within your code, this usually involves
making a "top-level" `dataclass` that has other `dataclass` instances as attributes.
The `mini_cfg` library provides a couple of simple mechanism for converting 
the dictionaries produced by YAML/TOML to additional sub-`dataclass` objects.

The simplest method is to inherit your configuration classes from `mini_cfg.BaseConfig`.
Any sub-configuration attributes with a type hint that inherits from `mini_cfg.BaseConfig`
will automatically be converted from a dictionary to an instance of your class.
Example:
```toml
[reader_params]
reader = "abi_l1b"

[plot_params]
cmap = "viridis"
vmin = 0.0
vmax = 1.0
```
```python
@dataclasses.dataclass
class ReaderParams(mini_cfg.BaseConfig):
    reader: str

@dataclasses.dataclass
class PlotParams(mini_cfg.BaseConfig):
    cmap: str
    vmin: float
    vmax: float

# This doesn't need to inherit from mini_cfg.BaseConfig, but it can if you
# want for consistency or you need BaseConfig's other features.
@dataclasses.dataclass
class TopLevelConfig(mini_cfg.BaseConfig):
    reader_params: ReaderParams
    plot_params: PlotParams

config_file = pathlib.Path("example_config.toml")
config = mini_cfg.cfg_from_toml(config_file, TopLevelConfig)

print(config.reader_params)
print(config.plot_params)

# Give config params to sub-systems
data = read_data(config.reader_params)
plot_data(config.plot_params)
```

This produces the output:
```bash
ReaderParams(reader='abi_l1b')
PlotParams(cmap='viridis', vmin=0.0, vmax=1.0)
```

However, there may be cases where you don't want to or can't make your sub-configuration
classes inherit from `mini_cfg.BaseConfig`.  In this case, you can pass a list
of sub-configuration classes to `cfg_from_toml`, `cfg_from_yaml`, and `cfg_from_dict`.
```toml
[position]
lon = -90.0
lat = 30.0
```
```python
from library_you_did_not_write import coords

# Let's say coords has a class named Position that has the following definition:
# @dataclasses.dataclass
# class Position:
#   lon: float
#   lat: float

@dataclasses.dataclass
class Config:
    position: coords.Position


config_file = pathlib.Path("example_config.toml")

config = mini_cfg.cfg_from_toml(config_file, Config, sub_classes=[coords.Position])
print(config.position)
```




### Cascading Configuration

### Custom Conversions

### Errors

### Validation

### Custom Reader




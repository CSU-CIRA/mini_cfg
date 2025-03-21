# mini_cfg
A minimal, no dependency, library that assists with storing configuration
information in dataclasses and makes no assumptions about the high level
structure of your code. Compatible with
[pydantic](https://docs.pydantic.dev/latest/) for advanced configuration
validation. 

It is almost always desirable to move parameters for executable code into a
configuration file. This is easy to achieve using a `dataclass` and Python's
buit-in TOML reader. For simple applications, a few lines of code to instantiate
a `dataclass` from a dictionary read from a TOML file is usually sufficient.  
However, as your code starts becoming more complex you begin to accumulate more
boilerplate to organize configuration data, perform conversions from the raw
config input, and perform validation. This library was written to reduce the
amount of boilerplate code that needs to be written to handle common "advanced"
configuration use cases.  

At the moment, only TOML and YAML files are supported.  No external libraries
are necessary if you only use TOML files.  If you need to use YAML files then
the `pyyaml` library should be installed in your environment.  You may pass a
reader function that the library can use to read additional formats.

## Installation
If you are only using TOML files then you can install `mini_cfg` using the
following command:
```bash
pip install git+ssh://git@github.com/CSU-CIRA/mini_cfg.git
```

If you are using YAML files then you can install `mini_cfg` with its optional
`pyyaml` dependency using the following command:
```bash
pip install 'mini_cfg[read_yaml] @ git+ssh://git@github.com/CSU-CIRA/mini_cfg.git'
```

## Usage

### Basics
To read a simple TOML configuration file into a dataclass, the `cfg_from_toml`
function can be used.  You simply provide it the config filename and the class
that should be constructed:

`example.toml`:
```toml
foo = 10
```

Python to read the TOML file into a `dataclass`:
```python
import dataclasses
import pathlib

from mini_cfg import mini_cfg

@dataclasses.dataclass
class Config:
    foo:int

config_file = pathlib.Path("example.toml")

# We just need to give cfg_from_toml the config filename and the class that is 
# being constructed from the config.
config = mini_cfg.cfg_from_toml(config_file, Config)
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

`Optional` attributes as well as attributes with default values are fully supported:

`example.toml`:
```toml
foo = 10
# The flag and optional entries are not provided in the file, so their default
# values will be used.
```
```python
@dataclasses.dataclass
class Config:
    foo:int
    flag: bool = False
    optional: Optional[str] = None

config_file = pathlib.Path("example.toml")

config = mini_cfg.cfg_from_toml(config_file, Config)
print(config)
```

This produces the output:
```
Config(foo=10, flag=False, optional=None)
```

### Automatic pathlib/datetime Conversion

#### pathlib.Path Conversions
It is usually preferable to represent paths using `pathlib.Path` objects rather
than storing them as strings.  However, TOML/YAML parsers do not automatically
produce `pathlib.Path` objects. Converting strings to paths can produce a lot of
boilerplate code.  By default, any attribute of your `dataclass` whose type hint
is `pathlib.Path` will have its value converted from `str` to `pathlib.Path`.
To disable this behaviour, you can pass `convert_paths=False` to
`cfg_from_toml`/`cfg_from_yaml`/`cfg_from_dict`/`cfg_from_file`.

`example.toml`:
```toml
some_file = "path/to/file.txt"
``` 

Python to demonstrate automatic conversion to `Path`s as well as disabling 
conversion:
```python
@dataclasses.dataclass
class Config:
    # Our attribute has a pathlib.Path type hint, so mini_cfg will try to
    # convert the value read from the config file to pathlib.Path.
    some_file: pathlib.Path

config_file = pathlib.Path("example.toml")

config = mini_cfg.cfg_from_toml(config_file, Config)
config_conversion_disabled = mini_cfg.cfg_from_toml(
    config_file, Config, convert_paths=False)

print(config.some_file, " ", type(config.some_file))
print(config.some_file, " ", type(config_conversion_disabled.some_file))
```    

This will produce the output:
```
path/to/file.txt   <class 'pathlib.PosixPath'>
path/to/file.txt   <class 'str'>
```

#### Datetime Conversions
When given a full ISO-8601 time, `pyyaml` and `tomllib` will produce a
`datetime` object.  However, when they are given just an ISO-8601 year, month,
and day they will produce a `date` object instead.  This can cause a problem if
downstream code assumes that hours, minutes, seconds, etc. are always available
in the objects they are given.  Additionally a dictionary obtained outside of a
YAML or TOML file may represent times as strings.  By default, any attribute of
your `dataclass` whose type hint is `datetime` will have its value converted to
`datetime`.  To disable this behaviour, you can pass `convert_dates=False` to
`cfg_from_toml`/`cfg_from_yaml`/`cfg_from_dict`/`cfg_from_file`.  The actual
value of the attribute prior to conversion may be a `datetime` object, a `date`
object, or a string representing an ISO-8601 compatible date.

`example.toml`:
```toml
foo = 2025-02-28
```

Python to demonstrate automatic conversion to `datetime` as well as disabling 
conversion:
```python
import datetime as dt

@dataclasses.dataclass
class Config:
    foo: dt.datetime


config_file = pathlib.Path("example.toml")

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
```
2025-02-28 00:00:00   <class 'datetime.datetime'>
2025-02-28   <class 'datetime.date'>
2025-02-28 00:00:00   <class 'datetime.datetime'>
```

### Hierarchical Configuration

#### Sub-Configuration Classes
Although it is possible to have a flat configuration where all the parameters
are part of a single large configuration object, it is usually beneficial to
split parameters into sections by sub-system.  Within your code, this usually
involves making a "top-level" `dataclass` that has other `dataclass` instances
as attributes. The `mini_cfg` library provides a couple of simple mechanisms for
converting the dictionaries produced by YAML/TOML to additional sub-`dataclass`
objects.

The simplest method is to inherit your configuration classes from
`mini_cfg.BaseConfig`. Any sub-configuration attributes with a type hint that
inherits from `mini_cfg.BaseConfig` will automatically be converted from a
dictionary to an instance of your class.

`example.toml`:
```toml
[reader_params]
reader = "abi_l1b"
file_glob = "*.nc"

[plot_params]
cmap = "viridis"
vmin = 0.0
vmax = 1.0
```

Python demonstrating conversion of "sub-configuration" `dataclass` objects: 
```python
@dataclasses.dataclass
class ReaderParams(mini_cfg.BaseConfig):
    reader: str
    file_glob: str

@dataclasses.dataclass
class PlotParams(mini_cfg.BaseConfig):
    cmap: str
    vmin: float
    vmax: float

# Because this is the "top" of the hierarchy and its class is being passed 
# directly to cfg_from_toml, this doesn't need to inherit from 
# mini_cfg.BaseConfig. It can if you want for consistency or if you need 
# BaseConfig's validation feature.
@dataclasses.dataclass
class TopLevelConfig(mini_cfg.BaseConfig):
    reader_params: ReaderParams
    plot_params: PlotParams

config_file = pathlib.Path("example.toml")
config = mini_cfg.cfg_from_toml(config_file, TopLevelConfig)

print(config.reader_params)
print(config.plot_params)

# Give config params to sub-systems
data = read_data(config.reader_params)
plot_data(config.plot_params)
```

This produces the output:
```
ReaderParams(reader='abi_l1b')
PlotParams(cmap='viridis', vmin=0.0, vmax=1.0)
```

However, there may be cases where you don't want to or can't make your
sub-configuration classes inherit from `mini_cfg.BaseConfig`.  In this case, you
can pass a list of sub-configuration classes to `cfg_from_toml`,
`cfg_from_yaml`, `cfg_from_dict`, and `cfg_from_file`.

`example.toml`:
```toml
[position]
lon = -90.0
lat = 30.0
```

Python demonstrating how to explicitly specify the sub-configuration classes 
that should be converted:
```python
from library_you_did_not_write import coords

# Let's say the coords module has a class named Position that has the following
# definition:
# @dataclasses.dataclass
# class Position:
#   lon: float
#   lat: float

@dataclasses.dataclass
class Config:
    position: coords.Position


config_file = pathlib.Path("example.toml")

sub_classes = [coords.Position]
config = mini_cfg.cfg_from_toml(config_file, Config, sub_classes=sub_classes)
print(config.position)
```

#### Sub-Configuration File Pointers
When using configuration files it is very common to find that a block of
parameters will be copy-pasted among several config files. This can lead to
problems common when copy-paste is used. For example, you may have several
config files for processing data from different satellite sources, but they all
share the same plotting parameters. To solve this, you copy-paste the plotting
parameters across your files.  But then you need to change a single plotting
parameter.  This requires you to change this parameter in all of you files.  

To avoid this problem, `mini_cfg` allows your config files to point to another
file when specifying sub-configuration objects.  The file will be read and
converted to your sub-configuration class.  So in the above example, you can
make a single config file containing your plotting parameters.  Your other
config files would then all point to the file containing your plotting
parameters.

`example.toml`:
```toml
plot_params = "plot_params.toml"
```

`plot_params.toml`:
```toml
cmap = "viridis"
vmin = 0.0
vmax = 1.0
```

This is all handled internally to `mini_cfg`, so nothing needs to be done in
your code to use this feature:
```python
@dataclasses.dataclass
class PlotParams(mini_cfg.BaseConfig):
    cmap: str
    vmin: float
    vmax: float

@dataclasses.dataclass
class Config(mini_cfg.BaseConfig):
    plot_params: PlotParams

config_file = pathlib.Path("example.toml")
config = mini_cfg.cfg_from_toml(config_file, Config)

print(config.plot_params.cmap)
```

This does not work with `cfg_from_dict` since that function will not know how
to read the sub-configuration file.

If a cycle is created via these file pointers, then a `ValueError` will be
thrown when the files are parsed.

### Cascading Configuration
It is frequently desirable to override a handful of parameters rather than alter
a config file.  For example, you may have a config setup for your code, but for
debugging purposes you would like to change a few parameters. Rather than
altering your file and potentially forgetting to change parameters back to what
they were, `mini_cfg` allows you to overwrite parameters by providing a file
"cascade" to `cfg_from_toml`, `cfg_from_yaml`, or `cfg_from_file`. 

Instead of passing an individual config file to these functions, you can provide
a list of files.  Each file will be read and recursively merged such that files
that appear later in the list will overwrite entries that appeared in earlier
files or add entries that were not present in earlier files.

`example.toml`
```toml
foo = 10

[plot_params]
cmap = "viridis"
vmin = 0.0
vmax = 1.0
```

`debug.toml`
```toml
# Overwrites foo
foo = 999 
# Since debug_flag was not included in example.toml, the resulting Config
# object would have used the default value of false.  However, we're including
# it here so it gets set to true.
debug_flag = true 

[plot_params]
# Overwrites cmap value
cmap = "gray"
# Since vmin/vmax are not provided here, their values from example.toml will
# be used.
```

```python
@dataclasses.dataclass
class PlotParams(mini_cfg.BaseConfig):
    cmap: str
    vmin: float
    vmax: float

@dataclasses.dataclass
class Config(mini_cfg.BaseConfig):
    foo: int
    plot_params: PlotParams

    debug_flag:bool = False

config_file = pathlib.Path("example.toml")
debug_file = pathlib.Path("debug.toml")
cascade = [config_file, debug_file]

config = mini_cfg.cfg_from_toml(cascade, Config)
print(config)
```

This produces the output:
```
Config(foo=999, plot_params=PlotParams(cmap='gray', vmin=0.0, vmax=1.0), debug_flag=True)
```

The cascade is evaluated *before* any sub-config conversion is performed.  This
means that use of both a cascade and sub-config file pointers may behave
unintuitively or potentially cause parsing to fail. 

If use of a cascade is preferable to you, it can be used instead of file
pointers to achieve the same effect.  As an example, you could store general
options in a config and plotting parameters in a second config. You could then
create a cascade that merges both files together.

### Custom Conversions
It is also possible to perform custom conversions by providing `cfg_from_toml`,
`cfg_from_yaml`, `cfg_from_dict`, or `cfg_from_file` with a dictionary that maps
classes to a Callable that will convert the config value to that class.

`example.toml`:
```toml
regex = 'foo\S+nc'
```

Python demonstrating custom conversion used to convert the string in the TOML
file to a regular expression:
```python
import re

@dataclasses.dataclass
class Config:
    regex: re.Pattern

config_file = pathlib.Path("example.toml")
# Any config attribute that has a type hint of re.Pattern will have re.compile
# called on its value to convert it to a re.Pattern.
converters = {re.Pattern:re.compile}
config = mini_cfg.cfg_from_toml(config_file, Config, converters=converters)

if config.regex.match("foobar.nc") is not None:
    print("Regex match!")
```

### Errors
If an error occurs while making use of file pointers or cascading, it can become
difficult to determine which config file caused the problem.  For that reason,
`mini_cfg` adds extra information to any `Exception`s encountered while parsing
config files.  The history of each parsed file is included at the bottom of the
exception's stack trace.  The most recently parsed file is included at the top
of the history and the oldest parsed file is at the bottom.  Each line in the
history also includes the config class that was being converted.

Example file history:
```
FileNotFoundError: [Errno 2] No such file or directory: 'does_not_exist.toml'
Error creating config type: <class '__main__.PlotParams'> from cascade: ['does_not_exist.toml']
Error creating config type: <class '__main__.Config'> from cascade: ['example.toml']
```
The above error was created because `example.toml` used a file pointer that refered
to a file that does not exist for its `PlotParams` sub-configuration.


### Validation
By using `dataclasses` to store configuration, some validation is performed by
simply constructing the class. For example, you will receive an error if your
config omits a required attribute.  However, any validation that requires
inspecting the values of an attribute will not be performed without additional
code.  

The `mini_cfg` library provides a simple mechanism for performing additional
validation.  The `mini_cfg.BaseConfig` class provides the `validate` method.
This method will recursively call the `_do_validation` method on itself and any
attributes that are also child classes of `mini_cfg.BaseConfig`.  Your config
classes can then implement `_do_validation` to inspect and validate attributes
in your instance.

Example:
```python
@dataclasses.dataclass
class Config(mini_cfg.BaseConfig):
    foo: int

    def _do_validation(self) -> None:
        if self.foo == -999:
            raise ValueError("Foo must not be -999.")
```

More advanced validation can be perfomed with the 
[pydantic](https://docs.pydantic.dev/latest/) library:

`example.toml`:
```toml
foo = "2025-02-28"
[plot_params]
# This should be a string with a colormap, not an integer
cmap = 10
vmin = 0.0
vmax = 1.0
```

```python
import datetime as dt
import pydantic

class PlotParams(pydantic.BaseModel):
    cmap: str
    vmin: float
    vmax: float

class Config(pydantic.BaseModel):
    foo: dt.datetime
    plot_params: PlotParams

config_file = pathlib.Path("example.toml")
config = mini_cfg.cfg_from_toml(config_file, Config, sub_classes=[PlotParams])
```

This produces the output:
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Config
plot_params.cmap
  Input should be a valid string [type=string_type, input_value=10, input_type=int]
    For further information visit https://errors.pydantic.dev/2.10/v/string_type
Error creating config type: <class '__main__.Config'> from cascade: ['example.toml']
```

### Custom Reader
Using `mini_cfg` with a custom reader is very simple.  Create a function that 
takes a `pathlib.Path` object and returns a `Dict` by parsing the file.
You can then pass your reader function to `cfg_from_file`.

```python
def read_json(path: pathlib.Path) -> Dict[str, Any]:
    import yaml

    with open(path, "r") as in_file:
        return json.load(in_file)

...

config = mini_cfg.cfg_from_file(config_file, Config, reader=read_json)
```

`mini_cfg` provides a parameterized integration test suite to make testing a new
reader relatively straightforward.  To use this test suite, write a
`unittest.TestCase` that calls `mini_cfg.file_test_suite.perform_tests`. This
function takes a single parameter which is a
`mini_cfg.file_test_suite.TestFixture` object.  This is a `dataclass` that
simply stores the reader function being tested, the `TestCase` that is
performing the testing, and paths for a set of config files that will be used to
perform the tests.  You can see `tests/itests/itest_toml_config.py` as an
example for how to use the test suite. 

You will need to create a set of test config files with specific contents in
order to test your reader. See the `mini_cfg.file_test_suite` docstring for
details on how to create these config files. The
`tests/itests/test_configs/toml/` can be used as an example.

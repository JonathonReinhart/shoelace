# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations
import dataclasses
from pathlib import Path
import platform
import textwrap
from typing import Any, Mapping, Sequence

# TODO(jrreinhart): Use stdlib tomllib for Python 3.11+
# https://github.com/hukkin/tomli#building-a-tomlitomllib-compatibility-layer
# But note hukkin/tomli#219
import tomli as tomllib  # Debian: 'apt install python3-tomli'

from .qemu import DEFAULT_MEMORY


class ConfigError(Exception):
    pass


def _load_config(path: Path) -> Config:
    with path.open("rb") as f:
        try:
            data = ConfigDict(tomllib.load(f), path.parent)
        except tomllib.TOMLDecodeError as err:
            raise ConfigError(f"Parse error: {err}") from err

    cfg = Config.from_cfgdict(data.get_cfgdict("shoelace"))
    return cfg


def load_config(path: Path | None) -> Config:
    if path is None:
        return Config.default()
    return _load_config(path)


_NO_DEFAULT = object()


class ConfigDict:
    def __init__(self, data: dict, base_dir: Path | None):
        self.data = data

        if base_dir is not None:
            assert base_dir.is_dir()
        self.base_dir = base_dir

    @classmethod
    def empty(cls) -> ConfigDict:
        return cls(data={}, base_dir=None)

    def get(self, key: str, exptype: type, default: Any = _NO_DEFAULT) -> Any:
        if not key in self.data:
            if default is _NO_DEFAULT:
                raise ConfigError(f"Key not found: {key!r}")

            if isinstance(default, type):
                # default is a type, return an instance
                assert issubclass(default, exptype)
                return default()

            # default is an object, return it
            assert isinstance(default, (exptype, type(None)))
            return default

        value = self.data[key]
        if not isinstance(value, exptype):
            raise ConfigError(
                f"{key!r} of inappropriate type: {type(value).__name__}, "
                f"expected: {exptype.__name__}")

        return value

    def get_list(self, key: str, elem_type: type) -> list:
        result = self.get(key, list, list)
        for i, elem in enumerate(result):
            if not isinstance(elem, elem_type):
                raise ConfigError(
                    f"Element {i} of {key!r} is inappropriate type: "
                    f"{type(elem).__name__}, expected: {elem_type.__name__}")
        return result

    def get_dict(self, key: str) -> dict:
        return self.get(key, dict, dict)

    def get_cfgdict(self, key: str) -> ConfigDict:
        return ConfigDict(self.get_dict(key), base_dir=self.base_dir)

    def get_path(self, key: str) -> Path | None:
        path = self.get(key, str, None)
        if path is None:
            return None
        return self.convert_path(path)

    def convert_path(self, pathstr: str, must_exist: bool = True) -> Path:
        path = Path(pathstr).expanduser()
        if not path.is_absolute():
            if self.base_dir is None:
                raise ValueError("Cannot convert relative path because "
                                 "base_dir was not set.")
            path = self.base_dir / path
        if must_exist and not path.exists():
            raise ConfigError(f"Specified path not found: {path}")
        return path


def _indent(text: str, amount: int) -> str:
    indent = " " * amount
    return "\n".join(indent + line for line in text.splitlines())


class ConfigBase:
    def __str__(self) -> str:
        return "\n".join(
            f"{field.name}: {getattr(self, field.name)}"
            for field in dataclasses.fields(self)
        )


@dataclasses.dataclass(frozen=True)
class Config(ConfigBase):
    kernel: KernelConfig
    initrd: InitrdConfig
    qemu: QemuConfig

    @classmethod
    def from_cfgdict(cls, data: ConfigDict) -> Config:
        return cls(
            kernel=KernelConfig.from_cfgdict(data.get_cfgdict("kernel")),
            initrd=InitrdConfig.from_cfgdict(data.get_cfgdict("initrd")),
            qemu=QemuConfig.from_cfgdict(data.get_cfgdict("qemu")),
        )

    @classmethod
    def default(cls) -> Config:
        return cls.from_cfgdict(ConfigDict.empty())

    def __str__(self) -> str:
        lines = (
            "kernel:\n" + _indent(str(self.kernel), 4),
            "initrd:\n" + _indent(str(self.initrd), 4),
            "qemu:\n" + _indent(str(self.qemu), 4),
        )
        return "\n".join(lines)


@dataclasses.dataclass(frozen=True)
class KernelConfig(ConfigBase):
    image: Path
    modules_dir: Path | None
    args: Sequence[str]

    @classmethod
    def from_cfgdict(cls, data: ConfigDict) -> KernelConfig:
        # image
        image = data.get_path("image")
        use_host_kernel = False
        if not image:
            use_host_kernel = True
            image = Path("/boot/vmlinuz-" + platform.release())

        # modules_dir
        modules_dir = data.get_path("modules_dir")
        if not modules_dir and use_host_kernel:
            modules_dir = Path("/lib/modules")

        return cls(
            image=image,
            modules_dir=modules_dir,
            args=data.get_list("args", str),
        )


@dataclasses.dataclass(frozen=True)
class InitrdConfig(ConfigBase):
    modules: Sequence[str]
    ext_modules: Sequence[Path]
    files: Mapping[Path, Path]  # guestpath: hostpath

    @classmethod
    def from_cfgdict(cls, data: ConfigDict) -> InitrdConfig:
        return cls(
            modules=data.get_list("modules", str),
            ext_modules=[
                data.convert_path(p) for p in data.get_list("ext_modules", str)
            ],
            files={
                Path(gpath): data.convert_path(hpath)
                for gpath, hpath in data.get("files", dict, {}).items()
            },
        )


@dataclasses.dataclass(frozen=True)
class QemuConfig(ConfigBase):
    memory: str
    cpus: int
    options: Sequence[str]
    devices: Sequence[str]

    @classmethod
    def from_cfgdict(cls, data: ConfigDict) -> QemuConfig:
        return cls(
            memory=data.get("memory", str, DEFAULT_MEMORY),
            cpus=data.get("cpus", int, 1),
            options=data.get("options", list, []),
            devices=data.get("devices", list, []),
        )

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

from pathlib import Path
from typing import Any

# TODO(jrreinhart): Use stdlib tomllib for Python 3.11+
# https://github.com/hukkin/tomli#building-a-tomlitomllib-compatibility-layer
# But note hukkin/tomli#219
import tomli as tomllib  # Debian: 'apt install python3-tomli'


class ConfigError(Exception):
    pass


def _load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as err:
            raise ConfigError(f"Parse error: {err}") from err

    return data["shoelace"]


def load_config(path: Path|None) -> dict[str, Any]:
    if path is None:
        return {}
    return _load_config(path)

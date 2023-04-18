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

import argparse
from collections.abc import Mapping, Sequence
import logging
import os
from pathlib import Path
import platform
import shutil
import tempfile
from typing import IO

from .config import load_config, ConfigError
from .initrd import InitRD, install_busybox, copy_static_content, copy_modules
from .kernel import get_kernel_version
from .qemu import run_qemu


_KERNEL_INIT = "/init"

_log = logging.getLogger(__name__)


def _build_initrd(
    args: argparse.Namespace,
    file: IO[bytes],
    kernel_version: str,
    modules_basedir: Path | None,
    module_names: Sequence[str],
    ext_modules: Sequence[Path],
    extra_files: Mapping[Path, Path] | None = None,
) -> None:
    if extra_files is None:
        extra_files = {}

    with InitRD(file) as initrd:  # flushed and closed on exit
        install_busybox(initrd, args.busybox)

        if args.init:
            initrd.add_file(_KERNEL_INIT, args.init)
        else:
            initrd.add_symlink(path=_KERNEL_INIT, target="/bin/busybox")

        copy_static_content(initrd)

        if module_names or ext_modules:
            if not modules_basedir:
                raise Exception("modules basedir not set")
            copy_modules(initrd, kernel_version, modules_basedir, module_names, ext_modules)

        for vm_path, host_path in extra_files.items():
            initrd.add_file(vm_path, host_path)


def _readable_file_path(string: str) -> Path:
    p = Path(string)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"File not found: {p}")
    if not p.is_file():
        raise argparse.ArgumentTypeError(f"Not a file: {p}")
    if not os.access(p, os.R_OK):
        raise argparse.ArgumentTypeError(f"File not readable: {p}")
    return p


def setup_logging(args: argparse.Namespace) -> None:
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", type=_readable_file_path,
                        help="Path to a shoelace.toml config file")
    parser.add_argument("-i", "--init", type=_readable_file_path,
                        help="Program to run as init; if not given, busybox is used")
    parser.add_argument("--busybox", type=_readable_file_path,
                        help="Path to statically-linked busybox binary")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    # Config defaults to shoelace.toml in current dir, if present
    if args.config is None:
        path = Path("shoelace.toml")
        if path.exists():
            args.config = path

    if args.busybox is None:
        busybox = shutil.which("busybox")
        if busybox:
            args.busybox = _readable_file_path(busybox)
        else:
            args.error("busybox not provided or found")

    return args


def main() -> None:
    args = parse_args()
    setup_logging(args)

    ################
    # Process config
    try:
        config = load_config(args.config)
    except ConfigError as err:
        raise SystemExit(f"Config error: {err}")

    #print("Config:")
    #print(config)
    #raise SystemExit()

    # Get kernel version
    with config.kernel.image.open("rb") as f:
        kernel_ver_str = get_kernel_version(f)
    kernel_version = kernel_ver_str.split()[0]
    _log.info(f"Detected kernel version: %s", kernel_version)

    # Kernel args
    kernel_args = [
        "console=ttyS0",
        f"rdinit={_KERNEL_INIT}",
    ]
    if not args.debug:
        kernel_args.append("quiet")
    kernel_args += config.kernel.args

    # QEMU
    qemu_opts = list(config.qemu.options)
    for dev in config.qemu.devices:
        qemu_opts += ["-device", dev]

    # Build the initrd
    initrd_tempfile = tempfile.NamedTemporaryFile(
        prefix="shoelace_initrd_",
        suffix=".img",
        mode="wb",
    )
    with initrd_tempfile:  # deleted on exit
        _log.info(f"Building initrd tempfile: %s", initrd_tempfile.name)
        _build_initrd(
            args=args,
            file=initrd_tempfile.file,
            kernel_version=kernel_version,
            modules_basedir=config.kernel.modules_dir,
            module_names=config.initrd.modules,
            ext_modules=config.initrd.ext_modules,
            extra_files=config.initrd.files,
        )

        # Run QEMU!
        qemu_proc = run_qemu(
            kernel=config.kernel.image,
            initrd=Path(initrd_tempfile.name),
            kernel_args=kernel_args,
            memory=config.qemu.memory,
            cpus=config.qemu.cpus,
            qemu_opts=qemu_opts,
            debug_launch=args.debug,
        )
        with qemu_proc:
            qemu_proc.wait()

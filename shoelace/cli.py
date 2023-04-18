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
from collections.abc import Sequence
import logging
import os
from pathlib import Path
import platform
import shutil
import tempfile
from typing import IO

from .config import load_config, ConfigError
from .initrd import InitRD, install_busybox, copy_static_content, copy_modules
from .qemu import run_qemu


_KERNEL_INIT = "/init"

_log = logging.getLogger(__name__)


def _build_initrd(
    args: argparse.Namespace,
    file: IO[bytes],
    modules_dir: Path,
    module_names: Sequence[str],
) -> None:
    with InitRD(file) as initrd:  # flushed and closed on exit
        install_busybox(initrd, args.busybox)

        if args.init:
            initrd.add_file(_KERNEL_INIT, args.init)
        else:
            initrd.add_symlink(path=_KERNEL_INIT, target="/bin/busybox")

        copy_static_content(initrd)
        copy_modules(initrd, modules_dir, module_names)


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

    # Boot the host kernel
    kernel_bzimage = Path("/boot/vmlinuz-" + platform.release())
    modules_dir = Path("/lib/modules/") / platform.release()

    module_names = [
        "vsock",
        "vmw_vsock_virtio_transport",
        "virtio_pci",
    ]

    # Kernel args
    kernel_args = [
        "console=ttyS0",
        f"rdinit={_KERNEL_INIT}",
    ]
    if not args.debug:
        kernel_args.append("quiet")

    VM_CID = 7
    qemu_opts = [
        '-device', f'vhost-vsock-pci,id=vhost-vsock-pci0,guest-cid={VM_CID}',
    ]

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
            modules_dir=modules_dir,
            module_names=module_names,
        )

        # Run QEMU!
        qemu_proc = run_qemu(
            kernel=kernel_bzimage,
            initrd=Path(initrd_tempfile.name),
            kernel_args=kernel_args,
            qemu_opts=qemu_opts,
            debug_launch=args.debug,
        )
        with qemu_proc:
            qemu_proc.wait()

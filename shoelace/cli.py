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

from .initrd import InitRD, install_busybox, copy_static_content, copy_modules
from .qemu import run_qemu

def _build_initrd(
    args: argparse.Namespace,
    file: IO[bytes],
    modules_dir: Path,
    module_names: Sequence[str],
) -> None:
    with InitRD(file) as initrd:  # flushed and closed on exit
        install_busybox(initrd, args.busybox)

        if args.init:
            initrd.add_file("/init", args.init)
        else:
            initrd.add_symlink(path="/init", target="/bin/busybox")

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
    # TODO
    logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--init", type=_readable_file_path,
                        help="Program to run as init; if not given, busybox is used")
    parser.add_argument("--busybox", type=_readable_file_path,
                        help="Path to statically-linked busybox binary")

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

    # Boot the host kernel
    kernel_bzimage = Path("/boot/vmlinuz-" + platform.release())
    modules_dir = Path("/lib/modules/") / platform.release()

    module_names = [
        "vsock",
        "vmw_vsock_virtio_transport",
        "virtio_pci",
    ]

    kernel_args = [
        'quiet',
        'console=ttyS0',
		'rdinit=/init',
    ]

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
        _build_initrd(args, initrd_tempfile.file, modules_dir, module_names)

        #print(f"initrd tempfile: {initrd_tempfile.name}")
        #input("Press ENTER to continue")

        # Run QEMU!
        qemu_proc = run_qemu(
            kernel=kernel_bzimage,
            initrd=Path(initrd_tempfile.name),
            kernel_args=kernel_args,
            qemu_opts=qemu_opts,
        )
        with qemu_proc:
            qemu_proc.wait()

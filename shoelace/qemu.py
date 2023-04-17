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
import subprocess
from typing import Iterable

def run_qemu(
    kernel: Path,
    initrd: Path,
    kernel_args: Iterable[str],
    qemu_opts: Iterable[str],
) -> subprocess.Popen:
    """Run QEMU KVM

    Args:
      kernel: Path to kernel bzImage (vmlinuz-*)
      initrd: Path to initrd
    """
    kernel_cmdline = " ".join(kernel_args)

    qemu_args: list[str | Path] = [
        'qemu-system-x86_64',
        '-machine', 'accel=kvm',
        '-nographic',
        '-kernel', kernel,
        '-initrd', initrd,
        '-append', kernel_cmdline,
    ]
    qemu_args.extend(qemu_opts)

    #print("About to run:")
    #from pprint import pprint
    #pprint(qemu_args)
    #input("Press ENTER to continue")

    return subprocess.Popen(qemu_args)

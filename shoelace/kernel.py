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

from typing import BinaryIO

class InvalidKernelImage(Exception):
    pass


def _read_cstring(file: BinaryIO, encoding: str = "ascii") -> str:
    """Reads a C-string from a file at the current file position.

    A C-string is defined as a sequence of bytes, terminated by a NUL
    (0x00) byte.

    Args:
      file: The binary file from which to read.
      encoding: The string encoding to use.
        Must be NUL-safe (e.g., "ascii" or "utf-8").

    Returns:
      The decoded string read from the file, not including the NUL terminator.

    Raises:
      EOFError: The end of file was reached before the string was terminated.
    """
    buf = bytearray()
    while True:
        b = file.read(1)
        if not b:
            raise EOFError()
        if b == b"\x00":
            break
        buf += b
    return buf.decode(encoding)


def _pread_cstring(file: BinaryIO, offset: int, encoding: str = "ascii") -> str:
    """Reads a C-string from a file at a specific offset.

    A C-string is defined as a sequence of bytes, terminated by a NUL
    (0x00) byte.

    The file position is left unchanged.

    Args:
      file: The binary file from which to read.
      offset: The offset into the file at which to read.
      encoding: The string encoding to use.
        Must be NUL-safe (e.g., "ascii" or "utf-8").

    Returns:
      The decoded string read from the file, not including the NUL terminator.

    Raises:
      EOFError: The end of file was reached before the string was terminated.
    """
    orig_offset = file.tell()
    try:
        file.seek(offset)
        return _read_cstring(file, encoding)
    finally:
        file.seek(orig_offset)


def _pread(file: BinaryIO, offset: int, count: int) -> bytes:
    """Reads a file at a specific offset.

    The file position is left unchanged.

    Args:
      file: The binary file from which to read.
      offset: The offset into the file at which to read.
      count: The number of bytes to read.

    Returns:
      The data read from the file, always exactly "count" bytes.

    Raises:
      EOFError: The requested number of bytes could not be read.
    """
    orig_offset = file.tell()
    try:
        file.seek(offset)
        data = file.read(count)
        if len(data) != count:
            raise EOFError()
        return data
    finally:
        file.seek(orig_offset)


def get_kernel_version(image: BinaryIO) -> str:
    """Gets the full kernel version string from a Linux bzImage.

    Args:
      image: Linux kernel image, opened with open(path, "rb").
    Returns:
      The full kernel version string.

      This is kernel_version from linux/arch/x86/boot/version.c:

          const char kernel_version[] =
              UTS_RELEASE " (" LINUX_COMPILE_BY "@" LINUX_COMPILE_HOST ") "
              UTS_VERSION;

      Where:
          UTS_RELEASE is $(uname -r)
          UTS_VERSION is $(uname -v)

    Raises:
      InvalidKernelImage for any error parsing the kernel image.
    """
    # https://www.kernel.org/doc/Documentation/x86/boot.txt
    try:
        header = _pread(image, 0x202, 4)
        if header != b"HdrS":
            raise InvalidKernelImage()

        kernel_version = int.from_bytes(_pread(image, 0x20e, 2), "little")
        return _pread_cstring(image, 0x200 + kernel_version)
    except EOFError:
        raise InvalidKernelImage()

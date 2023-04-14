from __future__ import annotations
import contextlib
import logging
from pathlib import Path
from typing import Any, IO

# https://github.com/Changaco/python-libarchive-c
# Debian: `apt install python3-libarchive-c`
import libarchive  # type: ignore[import]

_log = logging.getLogger(__name__)


class InitRD:
    def __init__(self, file: IO[bytes]):
        self._exit_stack = contextlib.ExitStack()

        MODE = "wb"
        if file.mode != MODE:
            raise ValueError(f"File must be open with mode={MODE}")

        self._file = file

        archive = libarchive.custom_writer(
            write_func=lambda data: self._file.write(data),
            format_name="cpio_newc",
        )
        self._archive = self._exit_stack.enter_context(archive)

    def __enter__(self) -> InitRD:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._exit_stack.__exit__(*exc_info)

    def add_file(
        self,
        path: str | Path,
        contents: Path | bytes,
        permission: int | None = None,
    ) -> None:
        """Adds a file to the initrd.

        Args:
          path: Path in archive where file will reside.
          contents: Contents of file to add. Can be either a (host) path which
            will be read, or bytes which will be written directly.
          permission: File permission bits.
            If not given: If contents is a path, copied from the source file,
            otherwise set to 0o664.
        """
        if not isinstance(path, Path):
            path = Path(path)
        if not path.is_absolute():
            raise ValueError("path must be absolute")
        name = str(path)[1:]

        if isinstance(contents, Path):
            data = contents.read_bytes()
        elif isinstance(contents, bytes):
            data = contents
        else:
            raise ValueError(f"Invalid contents type: {type(contents)}")

        if permission is None:
            if isinstance(contents, Path):
                permission = contents.stat().st_mode & 0o777
            else:
                permission = 0o664

        _log.debug("Adding file to initrd: name=%s size=%d permission=%s", name, len(data), permission)

        self._archive.add_file_from_memory(
            entry_path=name,
            entry_size=len(data),
            entry_data=data,
            permission=permission,
        )

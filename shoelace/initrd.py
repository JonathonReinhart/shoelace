from __future__ import annotations
import contextlib
from enum import IntEnum
import logging
from pathlib import Path
import subprocess
from typing import Any, IO

# https://github.com/Changaco/python-libarchive-c
# Debian: `apt install python3-libarchive-c`
import libarchive  # type: ignore[import]
import libarchive.entry  # type: ignore[import]
import libarchive.ffi as _laffi  # type: ignore[import]

_log = logging.getLogger(__name__)


# TODO:
# python-libarchive-c added a linkname setter and entry.FileType enum in
# version 4.0, but Debian 11 ships version 2.9, so we hack this in ourselves.

# These add methods to libarchive.ffi namespace

# voidarchive_entry_set_symlink_type(struct archive_entry *entry, int type);
_laffi.ffi('entry_set_symlink_type', [_laffi.c_archive_entry_p, _laffi.c_int], None)

# void archive_entry_set_symlink_utf8(struct archive_entry *entry, const char *linkname);
_laffi.ffi('entry_set_symlink_utf8', [_laffi.c_archive_entry_p, _laffi.c_char_p], None)

class SymlinkType(IntEnum):
	FILE = 1
	DIRECTORY = 2

class FileType(IntEnum):
    NAMED_PIPE     = AE_IFIFO  = 0o010000  # noqa: E221
    CHAR_DEVICE    = AE_IFCHR  = 0o020000  # noqa: E221
    DIRECTORY      = AE_IFDIR  = 0o040000  # noqa: E221
    BLOCK_DEVICE   = AE_IFBLK  = 0o060000  # noqa: E221
    REGULAR_FILE   = AE_IFREG  = 0o100000  # noqa: E221
    SYMBOLIC_LINK  = AE_IFLNK  = 0o120000  # noqa: E221
    SOCKET         = AE_IFSOCK = 0o140000  # noqa: E221


class InitRD:
    def __init__(self, file: IO[bytes]):
        self._exit_stack = contextlib.ExitStack()

        self._dirs_added: set[str] = set()

        MODE = "wb"
        if file.mode != MODE:
            raise ValueError(f"File must be open with mode={MODE}")

        self._file = self._exit_stack.enter_context(file)

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
            raise ValueError(f"path must be absolute: {path!r}")
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

        self._create_directories_for(path)
        self._archive.add_file_from_memory(
            entry_path=name,
            entry_size=len(data),
            entry_data=data,
            permission=permission,
        )


    def _create_directories_for(self, path: Path):
        assert path.is_absolute()
        for dirp in reversed(path.parents):
            if dirp == Path("/"):
                continue
            self._create_directory(dirp)

    def _create_directory(self, path: Path, perm: int = 0o755):
        assert path.is_absolute()
        name = str(path)[1:]
        if name in self._dirs_added:
            return
        self._dirs_added.add(name)

        _log.debug("Creating directory in initrd: %s", name)

        with libarchive.entry.new_archive_entry() as entry_p:
            entry = libarchive.entry.ArchiveEntry(None, entry_p)
            entry.pathname = name
            _laffi.entry_set_filetype(entry_p, FileType.DIRECTORY)
            _laffi.entry_set_perm(entry_p, perm)
            _laffi.entry_set_size(entry_p, 0)

            _laffi.write_header(self._archive._pointer, entry_p)
            _laffi.write_finish_entry(self._archive._pointer)


    def add_symlink(
        self,
        path: str | Path,
        target: str | Path,
    ) -> None:
        """Adds a symlink at path, pointing to target."""
        # TODO: DRY with add_file
        if not isinstance(path, Path):
            path = Path(path)
        if not path.is_absolute():
            raise ValueError(f"path must be absolute: {path!r}")
        name = str(path)[1:]

        self._create_directories_for(path)

        _log.debug("Adding symlink to initrd: %s -> %s", name, target)

        # TODO: linkname setter and libarchive.entry.FileType enum were added
        # in 4.0 but Debian11 ships 2.9, so we have to hack it in ourselves
        #self._archive.add_file_from_memory(
        #    entry_path=name,
        #    entry_size=0,
        #    entry_data=b"",
        #    filetype=libarchive.entry.FileType.SYMBOLIC_LINK,
        #    linkpath=str(target),
        #)

        with libarchive.entry.new_archive_entry() as entry_p:
            entry = libarchive.entry.ArchiveEntry(None, entry_p)
            entry.pathname = name

            # https://github.com/libarchive/libarchive/blob/0fd2ed25d7/libarchive/test/test_write_disk_symlink.c#L223
            _laffi.entry_set_filetype(entry_p, FileType.SYMBOLIC_LINK)
            _laffi.entry_set_perm(entry_p, 0o777)
            _laffi.entry_set_symlink_type(entry_p, SymlinkType.FILE)
            _laffi.entry_set_size(entry_p, 0)

            target_path_utf8 = str(target).encode('utf-8')
            _laffi.entry_set_symlink_utf8(entry_p, _laffi.c_char_p(target_path_utf8))

            _laffi.write_header(self._archive._pointer, entry_p)
            _laffi.write_finish_entry(self._archive._pointer)



def install_busybox(initrd: InitRD, busybox: Path) -> None:
    # Ensure Busybox is statically-linked
    # TODO: Another way to do this without shelling out to file?
    output = subprocess.check_output(["file", str(busybox)], text=True)
    if not "statically linked" in output:
        raise Exception(f"Not statically-linked: {busybox}")

    installed_path = Path("/bin/busybox")

    initrd.add_file(installed_path, busybox)

    output = subprocess.check_output([str(busybox), "--list-full"], text=True)
    for app_path in output.splitlines():
        app_path = "/" + app_path
        _log.debug("Busybox app: %s", app_path)

        # XXX TODO: check for existing entries in archive?
        if "busybox" in app_path:
            continue

        initrd.add_symlink(path=app_path, target=installed_path)

Shoelace config
---------------
This document describes the structure of the Shoelace config file
(`shoelace.toml`). Shoelace uses [TOML](https://toml.io/) for configuration.

# Types
In addition to standard [TOML types](https://toml.io/en/v1.0.0), Shoelace
defines the following types:

## Path
TOML Type: [String][String]

A path to a file or directory. Can be one of:
- An absolute path (starts with `/`)
- A user-relative path (starts with `~`, e.g. `~/code/foo`)
- A relative path, relative to the directory of the config file.


# Configuration Sections

## `[shoelace.kernel]`
Kernel settings.

- **`image`**
  - Type: Path
  - Description: The Linux kernel to boot. This is a bzImage, typically named
    `vmlinuz`.

    If omitted or empty, the host kernel (`uname -r`) will be used.

- **`modules_dir`**
  - Type: Path
  - Description:  Modules directory corresponding to `kernel`.

    This is the `.../lib/modules` directory containing a subdirectory for the
    given kernel release (`uname -r`).

    For a custom kernel, this can be produced with
    `make modules_install INSTALL_MOD_PATH=/wherever/`
    and would be set here as `/wherever/lib/modules`.

- **`args`**
  - Type: [Array][Array] of [String][String]
  - Description: Additional kernel command-line arguments.


## `[shoelace.initrd]`
Initrd settings.

- **`modules`**
  - Type: [Array][Array] of [String][String]
  - Description: A list of module *names* to include and automatically load.

- **`ext_modules`**
  - Type: [Array][Array] of Path
  - Description: A list of out-of-tree module *paths* to include and
    automatically load.

- **`files`**
  - Type: [Table][Table] of [String][String] => Path
  - Description: Each key represents a guest path to be populated by the file
    at the path in the value.

    It is recommended to use a separate table (`[shoelace.initrd.files]`)
    rather than an inline table.

  - Example:
    ```
    [shoelace.initrd.files]
    "/bin/socat" = "~/src/socat/socat-static"
    ```

## `[shoelace.qemu]`
QEMU settings.

- **`memory`**
  - Type: [String][String]
  - Description: Amount of memory to give the VM, with an `M` or `G` suffix (e.g `2G`).
  - Default: 1G

- **`cpus`**
  - Type: [Integer][Integer]
  - Description: The number of CPU cores to give the VM.
  - Default: 1

- **`devices`**
  - Type: [Array][Array] of [String][String]
  - Description: Additional
    [QEMU devices](https://www.qemu.org/docs/master/system/device-emulation.html)
    (without the `-device` part).

- **`options`**
  - Type: [Array][Array] of [String][String]
  - Description: Additional arbitrary
    [QEMU command-line options](https://www.qemu.org/docs/master/system/invocation.html).



[String]: https://toml.io/en/v1.0.0#string
[Integer]: https://toml.io/en/v1.0.0#integer
[Array]: https://toml.io/en/v1.0.0#array
[Table]: https://toml.io/en/v1.0.0#table

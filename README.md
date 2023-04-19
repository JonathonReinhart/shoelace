Shoelace
--------
It pulls your boots together.

Shoelace launces tiny VMs for testing or isolation. It builds a tiny, minimal
[initrd](https://en.wikipedia.org/wiki/Initial_ramdisk) based on your
configuration, and boots your desired kernel. Typically, this kernel will be
the same kernel running the host.


## Getting Started
Install prerequisites. On Debian:
```
$ sudo apt install python3-libarchive-c busybox-static
```

Then install (as a user) with pip:
```
$ git clone sso://user/jrreinhart/shoelace
$ cd shoelace
$ pip install .
```

Run shoelace!
```
$ shoelace
```

In a couple of seconds, you should find yourself sitting at a busybox shell in
the guest.

Exit QEMU by pressing `Ctrl+A` then `X`.


## Configuration
By default, shoelace will run with an empty config that simply boots with your
host kernel and busybox.

Shoelace uses a [TOML](https://toml.io/) file for additional configuration.
A file named `shoelace.toml` in the current directory will be used automatically.
Otherwise, a config file can be specified with `-c`.

Here is a sample `shoelace.toml` file which enables
[VSOCK](https://man7.org/linux/man-pages/man7/vsock.7.html) sockets,
includes a static `socat` binary, and tweaks some QEMU settings:

```toml
[shoelace.initrd]
# List of modules to include in initrd and autoload
modules = [
    "vsock",
    "vmw_vsock_virtio_transport",
    "virtio_pci",
]

[shoelace.initrd.files]
"/bin/socat" = "./socat-static"

[shoelace.qemu]
memory = "2G"
cpus = 2
devices = [
    "vhost-vsock-pci,id=vhost-vsock-pci0,guest-cid=7",
]
```

See `CONFIG.md` for full configration details.


## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## License

Apache 2.0; see [`LICENSE`](LICENSE) for details.

## Disclaimer

This project is not an official Google project. It is not supported by
Google and Google specifically disclaims all warranties as to its quality,
merchantability, or fitness for a particular purpose.

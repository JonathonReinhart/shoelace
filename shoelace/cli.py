import argparse
from pathlib import Path
import platform
import tempfile

from .initrd import InitRD
from .qemu import run_qemu

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    # XXX temp
    parser.add_argument('initprog', type=Path)

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    # Boot the host kernel
    kernel_bzimage = Path("/boot/vmlinuz-" + platform.release())

    kernel_args = [
        'quiet',
        'console=ttyS0',
        #'root=/dev/ram0', #'rw',
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
        with initrd_tempfile.file as f:  # closed on exit
            with InitRD(f) as initrd:   # flushed on exit
                initrd.add_file("/init", args.initprog)  # TODO: mode?

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

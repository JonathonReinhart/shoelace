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

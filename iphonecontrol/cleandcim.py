#!/usr/bin/env python3
"""cleandcim - free space on the camera iPhone: delete everything under /var/mobile/Media/DCIM.

Every photo is already pulled to this PC by snap.py, so nothing is lost.
Same transport as snap.py: SSH (port 22) over USB via usbmuxd, root/alpine by default.
Usage: python cleandcim.py [--ssh-password alpine]
iter.sh runs it before each photo phase.
"""
import argparse

import paramiko

from iphoneview import usb_connect

DCIM = "/var/mobile/Media/DCIM"


def connect(user, password):
    t = paramiko.Transport(usb_connect(22))
    so = t.get_security_options()
    for attr, legacy in (
        ("key_types", ("ssh-rsa", "ssh-dss")),
        ("kex", ("diffie-hellman-group14-sha1", "diffie-hellman-group1-sha1",
                 "diffie-hellman-group-exchange-sha1")),
        ("ciphers", ("aes128-cbc", "aes256-cbc", "3des-cbc")),
        ("digests", ("hmac-sha1",)),
    ):
        for alg in legacy:
            if alg not in getattr(so, attr):
                try:
                    setattr(so, attr, list(getattr(so, attr)) + [alg])
                except ValueError:
                    pass
    t.connect(username=user, password=password)
    return t


def run(t, cmd):
    ch = t.open_session()
    ch.exec_command(cmd)
    out = ch.makefile().read().decode(errors="replace")
    return ch.recv_exit_status(), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ssh-password", default="alpine")
    ap.add_argument("--ssh-user", default="root")
    a = ap.parse_args()
    t = connect(a.ssh_user, a.ssh_password)
    try:
        # the phone has no tail/wc: trim on this side
        _, before = run(t, "df -h /var")
        _, files = run(t, f"find {DCIM} -type f")
        rc, err = run(t, f"rm -rf {DCIM}/* 2>&1")
        _, after = run(t, "df -h /var")
        count = len([f for f in files.splitlines() if f.strip()])
        print(f"DCIM files deleted: {count} rc={rc} {err.strip()}")
        print(f"/var before: {before.strip().splitlines()[-1]}")
        print(f"/var after:  {after.strip().splitlines()[-1]}")
    finally:
        t.close()


if __name__ == "__main__":
    main()

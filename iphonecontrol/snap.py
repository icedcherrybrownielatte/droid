#!/usr/bin/env python3
"""snap - take a photo with the iPhone back camera and pull it to this PC.

Needs: iphoneview.py running (for the tap API), OpenSSH on the jailbroken phone,
and the `open` package from Cydia (launches apps by bundle id).

Usage: python snap.py [--out photos] [--ssh-password alpine] [--shutter-x 320 --shutter-y 880]
Transport: SSH (port 22) tunnelled over USB via usbmuxd, same as iphoneview --usb.
"""
import argparse
import json
import os
import posixpath
import stat
import sys
import time
import urllib.request

import paramiko

from iphoneview import API_FILE, usb_connect

DCIM = "/var/mobile/Media/DCIM"
PHOTO_EXT = (".jpg", ".jpeg", ".png", ".heic")


def api(cfg, path, body=None):
    req = urllib.request.Request(
        cfg["url"] + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"X-Token": cfg["token"]},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read()


def list_photos(sftp):
    """{remote_path: mtime} for every photo under DCIM/*."""
    found = {}
    for d in sftp.listdir_attr(DCIM):
        if not stat.S_ISDIR(d.st_mode):
            continue
        sub = posixpath.join(DCIM, d.filename)
        for f in sftp.listdir_attr(sub):
            if f.filename.lower().endswith(PHOTO_EXT):
                found[posixpath.join(sub, f.filename)] = f.st_mtime
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="photos", help="local download folder")
    ap.add_argument("--ssh-password", default="alpine", help="iOS 'mobile'/'root' password")
    ap.add_argument("--ssh-user", default="root")
    ap.add_argument("--shutter-x", type=int, default=320)
    ap.add_argument("--shutter-y", type=int, default=880)
    ap.add_argument("--timeout", type=float, default=15, help="seconds to wait for the new photo")
    a = ap.parse_args()

    try:
        with open(API_FILE) as f:
            cfg = json.load(f)
    except OSError:
        sys.exit(f"{API_FILE} missing: start `python iphoneview.py --usb` first")

    t = paramiko.Transport(usb_connect(22))
    # old iOS sshd only offers legacy host keys / kex / ciphers; append whatever paramiko still supports
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
                    pass  # paramiko build does not support it
    t.connect(username=a.ssh_user, password=a.ssh_password)
    sftp = paramiko.SFTPClient.from_transport(t)
    try:
        before = set(list_photos(sftp))

        # launch Camera (opens on back camera by default)
        chan = t.open_session()
        chan.exec_command("open com.apple.camera")
        if chan.recv_exit_status() != 0:
            sys.exit("`open` failed: install the 'open' package from Cydia")
        time.sleep(2.5)  # camera app + preview warm-up

        api(cfg, "/tap", {"x": a.shutter_x, "y": a.shutter_y})

        deadline = time.time() + a.timeout
        new = []
        while time.time() < deadline and not new:
            time.sleep(0.5)
            new = sorted(set(list_photos(sftp)) - before)
        if not new:
            sys.exit("no new photo appeared: check phone is unlocked and shutter position "
                     "(--shutter-x/--shutter-y)")

        os.makedirs(a.out, exist_ok=True)
        for remote in new:
            local = os.path.join(a.out, posixpath.basename(remote))
            sftp.get(remote, local)
            print(local)
    finally:
        sftp.close()
        t.close()


if __name__ == "__main__":
    main()

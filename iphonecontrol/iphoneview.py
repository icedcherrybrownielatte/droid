#!/usr/bin/env python3
"""iphoneview - low-latency VNC viewer/controller for jailbroken iOS 5-10 (Veency).

Usage:  python iphoneview.py HOST [--port 5900] [--password PW] [--scale 0.6] [--raw]

Mouse: left drag = touch, middle click = Home button, right click = Lock button.
Keys : F1 = Home, F2 = Lock, typed text goes to the focused iOS text field.
"""
import argparse
import io
import json
import os
import secrets
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import struct
import sys
import threading
import time
import zlib

import numpy as np
import pygame

ENC_RAW, ENC_COPYRECT, ENC_HEXTILE, ENC_ZRLE = 0, 1, 5, 16
ENC_DESKTOPSIZE = -223

# Mouse buttons in RFB mask; Veency: btn2 (middle) = Home, btn3 (right) = Lock.
SPECIAL_KEYS = {
    pygame.K_RETURN: 0xFF0D, pygame.K_BACKSPACE: 0xFF08, pygame.K_TAB: 0xFF09,
    pygame.K_DELETE: 0xFFFF, pygame.K_LEFT: 0xFF51, pygame.K_UP: 0xFF52,
    pygame.K_RIGHT: 0xFF53, pygame.K_DOWN: 0xFF54, pygame.K_LSHIFT: 0xFFE1,
    pygame.K_RSHIFT: 0xFFE2, pygame.K_LCTRL: 0xFFE3, pygame.K_RCTRL: 0xFFE4,
}


class Reader:
    """Buffered exact-length socket reader."""

    def __init__(self, sock):
        self.sock, self.buf, self.pos = sock, b"", 0

    def read(self, n):
        while len(self.buf) - self.pos < n:
            chunk = self.sock.recv(max(65536, n))
            if not chunk:
                raise ConnectionError("connection closed")
            self.buf = self.buf[self.pos:] + chunk
            self.pos = 0
        out = self.buf[self.pos:self.pos + n]
        self.pos += n
        return out

    def u8(self):
        return self.read(1)[0]


def vnc_auth(challenge, password):
    from Crypto.Cipher import DES  # pycryptodome
    key = bytes(int(f"{b:08b}"[::-1], 2) for b in password.encode("latin1")[:8].ljust(8, b"\0"))
    return DES.new(key, DES.MODE_ECB).encrypt(challenge)


def usb_connect(port):
    """Open a TCP-like tunnel to `port` on the first USB iPhone via usbmuxd (iTunes)."""
    import plistlib

    def rpc(s, msg, tag):
        body = plistlib.dumps(msg)
        s.sendall(struct.pack("<IIII", 16 + len(body), 1, 8, tag) + body)
        hdr = b""
        while len(hdr) < 16:
            c = s.recv(16 - len(hdr))
            if not c:
                raise ConnectionError("usbmuxd closed")
            hdr += c
        n = struct.unpack("<I", hdr[:4])[0] - 16
        data = b""
        while len(data) < n:
            data += s.recv(n - len(data))
        return plistlib.loads(data)

    s = socket.create_connection(("127.0.0.1", 27015), timeout=5)  # Windows usbmuxd
    base = {"ClientVersionString": "iphoneview", "ProgName": "iphoneview"}
    devs = rpc(s, {**base, "MessageType": "ListDevices"}, 1).get("DeviceList", [])
    if not devs:
        raise ConnectionError("no USB device (install iTunes, unlock + trust the phone)")
    did = devs[0]["DeviceID"]
    s.close()
    s = socket.create_connection(("127.0.0.1", 27015), timeout=5)
    res = rpc(s, {**base, "MessageType": "Connect", "DeviceID": did,
                  "PortNumber": socket.htons(port)}, 2)
    if res.get("Number") != 0:
        raise ConnectionError(f"usb connect refused ({res.get('Number')}): is Veency/VNC server running on port {port}?")
    return s


class Viewer:
    def __init__(self, host, port, password, raw, usb=False):
        self.compress = not raw
        self.lock = threading.Lock()
        self.send_lock = threading.Lock()
        self.dirty = True
        self.alive = True
        self.fps_count = 0
        self.rtt = 0.0
        self.t_req = 0.0
        self.sock = usb_connect(port) if usb else socket.create_connection((host, port), timeout=10)
        if not usb:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(None)
        self.r = Reader(self.sock)
        self.handshake(password)
        self.zdec = zlib.decompressobj()
        # 32bpp, depth 24, little-endian, true colour, R<<16 G<<8 B -> bytes B,G,R,X
        self.send(struct.pack(">BxxxBBBBHHHBBBxxx", 0, 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
        encs = [ENC_ZRLE, ENC_HEXTILE, ENC_COPYRECT, ENC_RAW] if self.compress else [ENC_RAW]
        encs.append(ENC_DESKTOPSIZE)
        self.send(struct.pack(">BxH", 2, len(encs)) + b"".join(struct.pack(">i", e) for e in encs))
        self.request(False)

    # ---- protocol -------------------------------------------------
    def send(self, data):
        with self.send_lock:
            self.sock.sendall(data)

    def handshake(self, password):
        r = self.r
        ver = r.read(12)
        minor = 8 if ver >= b"RFB 003.008" else 7 if ver >= b"RFB 003.007" else 3
        self.send(b"RFB 003.00%d\n" % minor)
        if minor == 3:
            sec = struct.unpack(">I", r.read(4))[0]
            if sec == 0:
                raise ConnectionError(r.read(struct.unpack(">I", r.read(4))[0]).decode(errors="replace"))
        else:
            n = r.u8()
            if n == 0:
                raise ConnectionError(r.read(struct.unpack(">I", r.read(4))[0]).decode(errors="replace"))
            types = list(r.read(n))
            sec = 1 if 1 in types else 2 if 2 in types else None
            if sec is None:
                raise ConnectionError(f"unsupported security types {types}")
            self.send(bytes([sec]))
        if sec == 2:
            if password is None:
                raise ConnectionError("server wants a password: use --password")
            self.send(vnc_auth(r.read(16), password))
        if sec == 2 or minor == 8:
            if struct.unpack(">I", r.read(4))[0] != 0:
                raise ConnectionError("authentication failed")
        self.send(b"\x01")  # shared
        w, h = struct.unpack(">HH", r.read(4))
        r.read(16)
        r.read(struct.unpack(">I", r.read(4))[0])
        self.fb = np.zeros((h, w, 4), np.uint8)

    def request(self, incremental):
        h, w = self.fb.shape[:2]
        self.t_req = time.perf_counter()
        self.send(struct.pack(">BBHHHH", 3, 1 if incremental else 0, 0, 0, w, h))

    def pointer(self, mask, x, y):
        self.send(struct.pack(">BBHH", 5, mask, x, y))

    def key(self, down, sym):
        self.send(struct.pack(">BBxxI", 4, 1 if down else 0, sym))

    # ---- receive loop ---------------------------------------------
    def run(self):
        r = self.r
        try:
            while self.alive:
                t = r.u8()
                if t == 0:
                    self.read_update()
                elif t == 1:  # colour map: ignore
                    _, first, n = struct.unpack(">BHH", r.read(5))
                    r.read(n * 6)
                elif t == 3:  # cut text
                    r.read(3)
                    r.read(struct.unpack(">I", r.read(4))[0])
                elif t != 2:
                    raise ConnectionError(f"unknown message {t}")
        except Exception as e:
            if self.alive:
                print("disconnected:", e, file=sys.stderr)
        self.alive = False

    def read_update(self):
        r = self.r
        r.read(1)
        n = struct.unpack(">H", r.read(2))[0]
        resized = False
        # pipeline: ask for the next frame now so the phone captures while we decode
        self.request(True)
        with_lock_needed = []
        for _ in range(n):
            x, y, w, h, enc = struct.unpack(">HHHHi", r.read(12))
            if enc == ENC_DESKTOPSIZE:
                with self.lock:
                    self.fb = np.zeros((h, w, 4), np.uint8)
                resized = True
                continue
            if enc == ENC_RAW:
                data = np.frombuffer(r.read(w * h * 4), np.uint8).reshape(h, w, 4)
                with self.lock:
                    self.fb[y:y + h, x:x + w] = data
            elif enc == ENC_COPYRECT:
                sx, sy = struct.unpack(">HH", r.read(4))
                with self.lock:
                    self.fb[y:y + h, x:x + w] = self.fb[sy:sy + h, sx:sx + w].copy()
            elif enc == ENC_HEXTILE:
                self.hextile(x, y, w, h)
            elif enc == ENC_ZRLE:
                ln = struct.unpack(">I", r.read(4))[0]
                self.zrle(x, y, w, h, self.zdec.decompress(r.read(ln)))
            else:
                raise ConnectionError(f"unsupported encoding {enc}")
        with self.lock:
            self.fb[:, :, 3] = 255  # server X byte is 0 -> would render transparent
        self.fps_count += 1
        self.rtt = (time.perf_counter() - self.t_req) * 1000
        self.dirty = True
        if resized:
            self.request(False)

    def hextile(self, x0, y0, w, h):
        r, fb = self.r, self.fb
        bg = fg = b"\0\0\0\0"
        for ty in range(y0, y0 + h, 16):
            th = min(16, y0 + h - ty)
            for tx in range(x0, x0 + w, 16):
                tw = min(16, x0 + w - tx)
                f = r.u8()
                if f & 1:
                    t = np.frombuffer(r.read(tw * th * 4), np.uint8).reshape(th, tw, 4)
                    with self.lock:
                        fb[ty:ty + th, tx:tx + tw] = t
                    continue
                if f & 2:
                    bg = r.read(4)
                if f & 4:
                    fg = r.read(4)
                with self.lock:
                    fb[ty:ty + th, tx:tx + tw] = np.frombuffer(bg, np.uint8)
                    if f & 8:
                        for _ in range(r.u8()):
                            col = r.read(4) if f & 16 else fg
                            xy, wh = r.u8(), r.u8()
                            sx, sy = tx + (xy >> 4), ty + (xy & 15)
                            fb[sy:sy + (wh & 15) + 1, sx:sx + (wh >> 4) + 1] = np.frombuffer(col, np.uint8)

    def zrle(self, x0, y0, w, h, d):
        p = 0
        fb = self.fb
        for ty in range(y0, y0 + h, 64):
            th = min(64, y0 + h - ty)
            for tx in range(x0, x0 + w, 64):
                tw = min(64, x0 + w - tx)
                sub = d[p]
                p += 1
                rle, ps = sub & 128, sub & 127
                if ps == 1:
                    tile = np.array([d[p], d[p + 1], d[p + 2], 255], np.uint8)
                    p += 3
                    with self.lock:
                        fb[ty:ty + th, tx:tx + tw] = tile
                    continue
                pal = None
                if ps:
                    pal = np.empty((ps, 4), np.uint8)
                    pal[:, 3] = 255
                    pal[:, :3] = np.frombuffer(d, np.uint8, ps * 3, p).reshape(ps, 3)
                    p += ps * 3
                npx = tw * th
                if not rle:
                    if pal is None:  # raw CPIXELs
                        px = np.empty((npx, 4), np.uint8)
                        px[:, 3] = 255
                        px[:, :3] = np.frombuffer(d, np.uint8, npx * 3, p).reshape(npx, 3)
                        p += npx * 3
                    else:  # packed palette
                        bits = 1 if ps == 2 else 2 if ps <= 4 else 4
                        nb = (tw * bits + 7) // 8
                        rows = np.frombuffer(d, np.uint8, nb * th, p).reshape(th, nb)
                        p += nb * th
                        shifts = np.array([8 - bits * (i + 1) for i in range(8 // bits)], np.uint8)
                        idx = ((rows[:, :, None] >> shifts) & ((1 << bits) - 1)).reshape(th, -1)[:, :tw]
                        px = pal[idx.reshape(-1)]
                else:
                    px = np.empty((npx, 4), np.uint8)
                    i = 0
                    while i < npx:
                        if pal is None:
                            col = np.array([d[p], d[p + 1], d[p + 2], 255], np.uint8)
                            p += 3
                            run = 1
                            isrun = True
                        else:
                            b = d[p]
                            p += 1
                            col = pal[b & 127]
                            isrun = bool(b & 128)
                            run = 1
                        if isrun:
                            while True:
                                v = d[p]
                                p += 1
                                run += v
                                if v != 255:
                                    break
                        px[i:i + run] = col
                        i += run
                with self.lock:
                    fb[ty:ty + th, tx:tx + tw] = px.reshape(th, tw, 4)


API_FILE = os.path.join(os.path.expanduser("~"), ".iphoneview.json")


def start_api(v, port):
    """Local HTTP control API sharing the viewer's single VNC connection.

    GET  /info                      -> {width,height}
    GET  /screenshot[?scale=0.5]    -> PNG
    POST /tap     {x,y,hold_ms}     -> touch (framebuffer pixel coords)
    POST /swipe   {x1,y1,x2,y2,ms}
    POST /button  {name:"home"|"lock"}
    POST /type    {text}            ("\\n" = Return)
    Every request needs header  X-Token: <token from ~/.iphoneview.json>.
    """
    token = secrets.token_hex(16)

    def swipe(x1, y1, x2, y2, ms):
        steps = max(2, int(ms / 12))
        v.pointer(1, x1, y1)
        for i in range(1, steps + 1):
            time.sleep(ms / 1000 / steps)
            v.pointer(1, x1 + (x2 - x1) * i // steps, y1 + (y2 - y1) * i // steps)
        v.pointer(0, x2, y2)

    def press(bit):
        v.pointer(bit, 0, 0)
        time.sleep(0.05)
        v.pointer(0, 0, 0)

    def type_text(text):
        for c in text:
            sym = 0xFF0D if c == "\n" else ord(c) if ord(c) < 256 else 0x01000000 + ord(c)
            v.key(True, sym)
            v.key(False, sym)
            time.sleep(0.01)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body, ctype="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authed(self):
            ok = secrets.compare_digest(self.headers.get("X-Token", ""), token)
            if not ok:
                self.reply(401, {"error": "bad or missing X-Token"})
            return ok

        def do_GET(self):
            if not self.authed():
                return
            path, _, q = self.path.partition("?")
            if path == "/info":
                h, w = v.fb.shape[:2]
                return self.reply(200, {"width": w, "height": h, "connected": v.alive})
            if path == "/screenshot":
                scale = 1.0
                for kv in q.split("&"):
                    if kv.startswith("scale="):
                        scale = max(0.05, min(1.0, float(kv[6:])))
                with v.lock:
                    h, w = v.fb.shape[:2]
                    surf = pygame.image.frombuffer(v.fb, (w, h), "BGRA").convert()
                if scale != 1.0:
                    surf = pygame.transform.smoothscale(surf, (int(w * scale), int(h * scale)))
                buf = io.BytesIO()
                pygame.image.save(surf, buf, "x.png")
                return self.reply(200, buf.getvalue(), "image/png")
            self.reply(404, {"error": "not found"})

        def do_POST(self):
            if not self.authed():
                return
            try:
                d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path == "/tap":
                    x, y = int(d["x"]), int(d["y"])
                    v.pointer(1, x, y)
                    time.sleep(d.get("hold_ms", 60) / 1000)
                    v.pointer(0, x, y)
                elif self.path == "/swipe":
                    swipe(int(d["x1"]), int(d["y1"]), int(d["x2"]), int(d["y2"]), int(d.get("ms", 250)))
                elif self.path == "/button":
                    press({"home": 2, "lock": 4}[d["name"]])
                elif self.path == "/type":
                    type_text(d["text"])
                else:
                    return self.reply(404, {"error": "not found"})
                self.reply(200, {"ok": True})
            except (KeyError, ValueError, TypeError) as e:
                self.reply(400, {"error": f"bad request: {e!r}"})
            except OSError as e:
                self.reply(503, {"error": f"phone disconnected: {e}"})

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)  # loopback only
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with open(API_FILE, "w") as f:
        json.dump({"url": f"http://127.0.0.1:{srv.server_address[1]}", "token": token}, f)
    return srv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-port", type=int, default=8765, help="local control API port (0 = off)")
    ap.add_argument("host", nargs="?", help="phone IP (omit with --usb)")
    ap.add_argument("--usb", action="store_true", help="connect over USB via usbmuxd (needs iTunes)")
    ap.add_argument("--port", type=int, default=5900)
    ap.add_argument("--password")
    ap.add_argument("--scale", type=float, default=0.6, help="initial window scale")
    ap.add_argument("--compress", action="store_true", help="use ZRLE/Hextile (slower on old phones)")
    a = ap.parse_args()

    if not a.host and not a.usb:
        ap.error("give HOST or --usb")
    v = Viewer(a.host, a.port, a.password, not a.compress, a.usb)
    threading.Thread(target=v.run, daemon=True).start()
    if a.api_port:
        start_api(v, a.api_port)
        print(f"control API: see {API_FILE} (url + X-Token)")

    pygame.init()
    fh, fw = v.fb.shape[:2]
    screen = pygame.display.set_mode((int(fw * a.scale), int(fh * a.scale)), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    mask, mx, my, moved = 0, 0, 0, False
    keymap = {}
    last_title = 0.0
    redraw = True

    def to_fb(pos):
        fh, fw = v.fb.shape[:2]
        sw, sh = screen.get_size()
        s = min(sw / fw, sh / fh)
        ox, oy = (sw - fw * s) / 2, (sh - fh * s) / 2
        return (max(0, min(fw - 1, int((pos[0] - ox) / s))),
                max(0, min(fh - 1, int((pos[1] - oy) / s))))

    def tap(btn):  # press+release of a special button (2=Home, 3=Lock)
        bit = 1 << (btn - 1)
        v.pointer(bit, mx, my)
        v.pointer(0, mx, my)

    while v.alive:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                v.alive = False
            elif e.type in (pygame.VIDEORESIZE, pygame.WINDOWEXPOSED):
                redraw = True
            elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and e.button in (1, 2, 3):
                mx, my = to_fb(e.pos)
                bit = 1 << (e.button - 1)
                mask = mask | bit if e.type == pygame.MOUSEBUTTONDOWN else mask & ~bit
                v.pointer(mask, mx, my)
                moved = False
            elif e.type == pygame.MOUSEMOTION and mask:
                mx, my = to_fb(e.pos)
                moved = True
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F1:
                    tap(2)
                elif e.key == pygame.K_F2:
                    tap(3)
                else:
                    sym = SPECIAL_KEYS.get(e.key) or (ord(e.unicode) if e.unicode and e.unicode.isprintable() else None)
                    if sym:
                        keymap[e.key] = sym
                        v.key(True, sym)
            elif e.type == pygame.KEYUP and e.key in keymap:
                v.key(False, keymap.pop(e.key))
        if moved:  # coalesce motion: one pointer event per frame
            v.pointer(mask, mx, my)
            moved = False
        if v.dirty or redraw:
            with v.lock:
                v.dirty = False
                fh, fw = v.fb.shape[:2]
                surf = pygame.image.frombuffer(v.fb, (fw, fh), "BGRA")
                sw, sh = screen.get_size()
                s = min(sw / fw, sh / fh)
                size = (int(fw * s), int(fh * s))
                screen.fill((0, 0, 0))
                screen.blit(pygame.transform.scale(surf, size) if size != (fw, fh) else surf,
                            ((sw - size[0]) // 2, (sh - size[1]) // 2))
            pygame.display.flip()
            redraw = False
        now = time.time()
        if now - last_title > 1:
            pygame.display.set_caption(f"iPhone  {v.fps_count} fps  {v.rtt:.0f} ms")
            v.fps_count, last_title = 0, now
        clock.tick(120)
    pygame.quit()
    try:
        os.remove(API_FILE)
    except OSError:
        pass


if __name__ == "__main__":
    main()

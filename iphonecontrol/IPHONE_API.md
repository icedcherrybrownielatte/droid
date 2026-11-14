# Controlling the iPhone via iphoneview

The user runs `iphoneview.py` (a VNC viewer for a jailbroken iPhone). It exposes a local HTTP API that shares the user's existing connection. Do not start your own VNC session and do not launch the viewer yourself.

## Connect

Read `~/.iphoneview.json` (Windows: `C:\Users\User\.iphoneview.json`):

```json
{"url": "http://127.0.0.1:8765", "token": "..."}
```

If the file is missing, the viewer is not running: ask the user to start `python iphoneview.py --usb`.

Send the token on every request as header `X-Token: <token>`.

## Endpoints

Coordinates are phone pixels (e.g. 640x960), origin top-left. Check `/info` for the size.

| Call | Body | Effect |
|---|---|---|
| `GET /info` | | `{"width","height","connected"}` |
| `GET /screenshot?scale=0.5` | | PNG. `scale` 0.05-1.0; use 0.5 to save tokens |
| `POST /tap` | `{"x":100,"y":200,"hold_ms":60}` | tap (`hold_ms` optional) |
| `POST /swipe` | `{"x1":320,"y1":700,"x2":320,"y2":200,"ms":250}` | swipe/scroll (`ms` optional) |
| `POST /button` | `{"name":"home"}` or `{"name":"lock"}` | hardware button |
| `POST /type` | `{"text":"hello\n"}` | type into focused field; `\n` = Return |

Errors: 401 bad token, 400 bad body, 503 phone disconnected.

## Example (bash)

```bash
F=~/.iphoneview.json
URL=$(python -c "import json,os;print(json.load(open(os.path.expanduser('$F')))['url'])")
TOK=$(python -c "import json,os;print(json.load(open(os.path.expanduser('$F')))['token'])")
curl -s -H "X-Token: $TOK" "$URL/screenshot?scale=0.5" -o shot.png
curl -s -X POST -H "X-Token: $TOK" -d '{"x":320,"y":480}' "$URL/tap"
```

## Taking a photo with the back camera: `snap.py`

To take a photo and get the file onto the PC, run `snap.py` from this folder. Do not tap through the Camera app by hand.

```bash
python snap.py                 # saves to ./photos/ and prints each saved path
python snap.py --out shots     # choose the folder
```

Then read the printed image path to look at the photo.

What it does: it connects to the phone over SSH (port 22, tunnelled over USB), launches Camera with `open com.apple.camera`, taps the shutter through the API above, waits for the new file in `/var/mobile/Media/DCIM`, and downloads it.

Requirements:
- `iphoneview.py --usb` must be running, because `snap.py` needs `~/.iphoneview.json` to tap the shutter. Do not start it yourself; ask the user.
- The phone must be unlocked.
- The phone needs OpenSSH and the Cydia `open` package. Default login is `root` / `alpine`; override with `--ssh-user` and `--ssh-password`.
- Python `paramiko` must be 3.x (tested with 3.5.1). Version 4 and later cannot talk to the phone's old OpenSSH 6.7 (error: `no acceptable host key`). Do not upgrade it.

Options and failure modes:
- The shutter tap defaults to `(320, 880)`, assuming a 640x960 screen. If `snap.py` exits with "no new photo appeared", take a `/screenshot` while Camera is open, find the shutter button, and pass `--shutter-x` and `--shutter-y` in phone pixels.
- Camera normally opens on the back camera. `snap.py` does not check. If the photo is a selfie, take a `/screenshot` and tap the flip-camera button before running it again.
- The error "`open` failed" means the Cydia `open` package is missing on the phone.
- `--timeout` (default 15 s) is how long it waits for the new photo.

## Notes

- Screen updates at ~8 fps. After an action, wait ~0.3-0.5 s before taking a screenshot.
- Screenshot at the scale you chose: multiply coordinates by `1/scale` before tapping.
- The user may be using the window at the same time; avoid acting while they are dragging.
- Phone is iOS 5-10 era: screen is small, no gestures beyond touch, Home = `/button home`.

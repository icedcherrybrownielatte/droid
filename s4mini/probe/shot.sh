#!/bin/bash
# usage: shot.sh <out.png> [delay_seconds]  -- grab a rotated/upscaled webcam frame of the phone screen
D="$(cd "$(dirname "$0")/.." && pwd)"; OUT="$1"; case "$OUT" in /*|?:*) ;; *) OUT="$D/$OUT";; esac; cd "$D/recon/cam"
sleep "${2:-0}"
ffmpeg -hide_banner -loglevel error -y -f dshow -i video="OBS Virtual Camera" -frames:v 4 -update 1 raw.jpg
ffmpeg -hide_banner -loglevel error -y -i raw.jpg -vf "crop=1000:1080:0:0,transpose=1,scale=iw*1.6:ih*1.6:flags=lanczos,unsharp=5:5:1.5" "$OUT"

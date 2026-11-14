"""Take a photo of the S4 every N seconds (snap.py without the `open` exit-code check). Usage: snaploop.py count interval"""
import subprocess, sys, time
src = open('snap.py').read().replace(
    'if chan.recv_exit_status() != 0:\n            sys.exit("`open` failed: install the \'open\' package from Cydia")',
    'chan.recv_exit_status()')
open('_snap_noopen.py', 'w').write(src)
n, iv = int(sys.argv[1]), float(sys.argv[2])
for i in range(n):
    r = subprocess.run([sys.executable, '_snap_noopen.py', '--out', 'photos'], capture_output=True, text=True)
    print(time.strftime('%H:%M:%S'), (r.stdout.strip().splitlines() or ['?'])[-1], flush=True)
    time.sleep(iv)

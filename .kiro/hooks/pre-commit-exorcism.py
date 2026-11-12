import sys
import subprocess

def scan_for_ghosts():
    print("[!] NecroCD Hook: Scanning staging area for legacy cursed code...")
    result = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True)
    if "python2" in result.stdout or "var " in result.stdout:
        print("[!] POLTERGEIST WARNING: Deprecated syntax detected! Chanting auto-patch...")
    sys.exit(0)

if __name__ == "__main__":
    scan_for_ghosts()

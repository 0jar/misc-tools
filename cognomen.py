import argparse, sys, os, threading
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

SERVICES = {
    'github': 'https://github.com/{}', 'gitlab': 'https://gitlab.com/{}',
    'codeberg': 'https://codeberg.org/{}', 'minecraft': 'https://api.mojang.com/users/profiles/minecraft/{}',
    'lichess': 'https://lichess.org/@/{}', 'osu': 'https://osu.ppy.sh/users/{}',
    'hackernews': 'https://news.ycombinator.com/user?id={}', 'npm': 'https://www.npmjs.com/~{}',
    'docker': 'https://hub.docker.com/u/{}', 'hackerrank': 'https://www.hackerrank.com/{}',
    'devto': 'https://dev.to/{}', 'fosstodon': 'https://fosstodon.org/@{}',
    'codepen': 'https://codepen.io/{}', 'hackerone': 'https://hackerone.com/{}',
    'twitter': 'https://twitter.com/{}', 'instagram': 'https://www.instagram.com/{}',
    'tiktok': 'https://www.tiktok.com/@{}', 'youtube': 'https://www.youtube.com/@{}',
    'facebook': 'https://www.facebook.com/{}', 'tumblr': 'https://{}.tumblr.com/',
    'reddit': 'https://www.reddit.com/user/{}', 'telegram': 'https://t.me/{}'
}

print_lock = threading.Lock()

def check_username(sess, srv, u):
    try:
        r = sess.get(SERVICES[srv].format(quote(u)), timeout=5)
        ok = ("No such user" in r.text) if srv == 'hackernews' else (r.status_code in (404, 204))
        return u, srv, ok, r.status_code
    except requests.RequestException:
        return u, srv, False, "ERR"

def main():
    p = argparse.ArgumentParser(description="Check username availability across platforms.")
    p.add_argument('-o', '--out', default='avail.txt', help="Output file (default: avail.txt)")
    p.add_argument('-b', '--bl', help="Blacklist file (optional)")
    p.add_argument('-i', '--input', required=True, help="Input list of usernames as a file (one username per line)")
    p.add_argument('--all', action='store_true', help="Check all services")
    for s in SERVICES: p.add_argument(f'--{s}', action='store_true')
    p.add_argument('-c', '--custom', help="Custom service URL with '{}' as placeholder for username")
    args = p.parse_args()

    if args.custom:
        if '{}' not in args.custom: sys.exit("Error: Custom URL must contain '{}' placeholder.")
        SERVICES['custom'] = args.custom

    sel = [s for s in SERVICES if getattr(args, s, False) or args.all]
    if not sel: sys.exit("Error: Select at least one service or use --all.")

    bl = set()
    if args.bl:
        try:
            with open(args.bl) as f: bl = set(f.read().split())
        except FileNotFoundError: pass

    try:
        with open(args.input) as f:
            users = [u.strip() for u in f if u.strip() and u.strip() not in bl]
    except FileNotFoundError:
        sys.exit(f"Error: Input file '{args.input}' not found.")

    print(f"Checking {len(users)} names across {len(sel)} services...")
    sess = requests.Session()
    sess.headers.update({"User-Agent": "cognomen/1.0 (Username availability checker; +https://codeberg.org/0jar/misc-tools)"})

    avail_count = 0
    with open(args.out, 'a') as f, ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(check_username, sess, s, u): (u, s) for u in users for s in sel}
        for i, fut in enumerate(as_completed(futs), 1):
            u, s, ok, code = fut.result()
            with print_lock:
                sys.stdout.write(f"\x1b[2K\r({i}/{len(futs)}) {u}@{s} [{code}]")
                if ok:
                    avail_count += 1
                    sys.stdout.write(f"\x1b[2K\r[+] {u}@{s} available!\n")
                    f.write(f"{u} ({s})\n")
                    f.flush()
                sys.stdout.flush()
    print(f"\nDone, {avail_count} names available." + (" Check output file for available usernames." if avail_count > 0 else ""))

if __name__ == "__main__": main()

#!/usr/bin/env python3
import argparse, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

def check(url, sess, to=10):
    if not url.startswith('http'): url = 'http://' + url
    try:
        with sess.get(url, timeout=to, stream=True) as r:
            if r.status_code == 404:
                return url, "404"
            if len(r.history) > 1:
                chain = " -> ".join(str(x.status_code) for x in r.history)
                return url, f"Redirect chain ({chain} -> {r.status_code})"
            if r.status_code >= 400 and r.status_code != 404:
                return url, f"{r.status_code}"
    except requests.exceptions.Timeout: return url, "Timeout"
    except requests.exceptions.TooManyRedirects: return url, "Too many redirects"
    except requests.RequestException as e: return url, f"Error: {type(e).__name__}"
    return url, None

def main():
    p = argparse.ArgumentParser(description="Dead link checker.")
    p.add_argument('urls', nargs='*', help="URLs to check")
    p.add_argument('-f', '--file', help="Local file with URLs (one per line)")
    p.add_argument('-w', '--workers', type=int, default=10, help="Number of concurrent workers")
    args = p.parse_args()

    urls = set(args.urls)
    if args.file:
        try: urls.update(l.strip() for l in open(args.file) if l.strip())
        except OSError: sys.exit(f"Error: reading {args.file}")
    if not urls: sys.exit(p.format_help())

    sess = requests.Session()
    sess.headers.update({"User-Agent": "linkrot/1.0 (Jarema's dead link checker; +https://codeberg.org/0jar/misc-tools)"})

    print(f"Checking {len(urls)} URLs...")
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(check, u, sess) for u in urls]
        for fut in as_completed(futs):
            u, err = fut.result()
            if err: print(f"[{err}] {u}")

if __name__ == "__main__": main()

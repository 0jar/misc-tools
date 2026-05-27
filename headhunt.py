#!/usr/bin/env python3
import sys, json, argparse, requests
from html.parser import HTMLParser

class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {"title": "", "desc": None, "canonical": None}
        self.ogs, self.jsonld, self.h_classes = {}, [], set()
        self._in, self._buf = None, []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'title':
            self._in, self._buf = 'title', []
        elif tag == 'meta':
            n, p, c = d.get('name', '').lower(), d.get('property', '').lower(), d.get('content')
            if n == 'description': self.meta['desc'] = c
            elif p.startswith('og:'): self.ogs[p] = c
        elif tag == 'link' and d.get('rel') == 'canonical':
            self.meta['canonical'] = d.get('href')
        elif tag == 'script' and d.get('type') == 'application/ld+json':
            self._in, self._buf = 'jsonld', []

        self.h_classes.update(c for c in d.get('class', '').split() if c in {
            'h-card', 'h-entry', 'h-feed', 'h-event', 'h-review',
            'h-review-aggregate', 'h-recipe', 'h-resume', 'h-product',
            'h-item', 'h-geo', 'h-adr'})

    def handle_endtag(self, tag):
        if self._in == 'title' and tag == 'title':
            self.meta['title'] = "".join(self._buf).strip()
        elif self._in == 'jsonld' and tag == 'script':
            self.jsonld.append("".join(self._buf))
        else: return
        self._in = None

    def handle_data(self, data):
        if self._in: self._buf.append(data)

def main():
    p = argparse.ArgumentParser(description="Fetch and extract metadata from a URL.")
    p.add_argument('url', help="URL to fetch")
    args = p.parse_args()

    url = args.url if '://' in args.url else 'https://' + args.url
    if not url.startswith(('http://', 'https://')):
        sys.exit("Error: Only HTTP(S) URLs are supported.")

    try:
        r = requests.get(url, timeout=10, stream=True, headers={
            "User-Agent": "headhunt/1.0 (Jarema's header metadata fetcher; +https://codeberg.org/0jar/misc-tools)"
        })
        r.raise_for_status()

        html = ""
        for chunk in r.iter_content(chunk_size=65536, decode_unicode=True):
            html += chunk if isinstance(chunk, str) else chunk.decode(r.encoding or 'utf-8', errors='ignore')
            if len(html) > 1024 * 1024: break
    except Exception as e:
        sys.exit(f"Error fetching URL: {e}")

    parser = MetaParser()
    parser.feed(html)

    print(f"URL: {url}")
    print(f"Title: {parser.meta['title'] or 'None'}")
    print(f"Description: {parser.meta['desc'] or 'None'}")
    print(f"Canonical URL: {parser.meta['canonical'] or 'None'}")

    print("\nOpengraph tags:")
    for k, v in parser.ogs.items(): print(f"  {k}: {v}")
    if not parser.ogs: print("  None")

    print("\nMicroformats (JSON-LD):")
    for j in parser.jsonld:
        try: print("  " + "\n  ".join(json.dumps(json.loads(j), indent=2).splitlines()))
        except json.JSONDecodeError: print("  [Invalid JSON-LD]")
    if not parser.jsonld: print("  None")

    print("\nMicroformats (HTML classes):")
    for c in sorted(parser.h_classes): print(f"  {c}")
    if not parser.h_classes: print("  None")

if __name__ == "__main__": main()

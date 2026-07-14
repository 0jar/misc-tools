#!/usr/bin/env python3
import sys
import argparse
import base64
import urllib.parse
import html
import re
import hashlib

def get_words(text):
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    return text.split()

def main():
    p = argparse.ArgumentParser(description="Convert text between encodings and standard case types.")
    p.add_argument("text", nargs="*", help="Text to convert (can also be piped via stdin)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("-e", "--encode", choices=["b64", "url", "html", "hex", "bin"], help="Encode text (base64, url, html, hex, binary)")
    g.add_argument("-d", "--decode", choices=["b64", "url", "html", "hex", "bin"], help="Decode text (base64, url, html, hex, binary)")
    g.add_argument("--hash", choices=["md5", "sha1", "sha256", "sha512"], help="Hash text (md5, sha1, sha256, sha512)")
    g.add_argument("--reverse", action="store_true", help="Reverse string")
    g.add_argument("--upper", action="store_true", help="UPPERCASE")
    g.add_argument("--lower", action="store_true", help="lowercase")
    g.add_argument("--title", action="store_true", help="Title Case")
    g.add_argument("--camel", action="store_true", help="camelCase")
    g.add_argument("--pascal", action="store_true", help="PascalCase")
    g.add_argument("--snake", action="store_true", help="snake_case")
    g.add_argument("--screaming-snake", action="store_true", help="SCREAMING_SNAKE_CASE")
    g.add_argument("--kebab", action="store_true", help="kebab-case")

    args = p.parse_args()

    if args.text:
        text = " ".join(args.text)
    elif not sys.stdin.isatty():
        text = sys.stdin.read().rstrip('\r\n')
    else:
        sys.exit(p.format_help())

    if not text:
        sys.exit("Error: No text provided.")

    try:
        if args.encode == "b64": out = base64.b64encode(text.encode()).decode()
        elif args.encode == "url": out = urllib.parse.quote(text)
        elif args.encode == "html": out = html.escape(text)
        elif args.encode == "hex": out = text.encode().hex()
        elif args.encode == "bin": out = ' '.join(format(x, '08b') for x in text.encode())
        elif args.decode == "b64": out = base64.b64decode(text).decode()
        elif args.decode == "url": out = urllib.parse.unquote(text)
        elif args.decode == "html": out = html.unescape(text)
        elif args.decode == "hex": out = bytes.fromhex(text.replace(' ', '')).decode()
        elif args.decode == "bin": out = bytes(int(b, 2) for b in text.split()).decode()
        elif args.hash == "md5": out = hashlib.md5(text.encode()).hexdigest()
        elif args.hash == "sha1": out = hashlib.sha1(text.encode()).hexdigest()
        elif args.hash == "sha256": out = hashlib.sha256(text.encode()).hexdigest()
        elif args.hash == "sha512": out = hashlib.sha512(text.encode()).hexdigest()
        elif args.reverse: out = text[::-1]
        elif args.upper: out = text.upper()
        elif args.lower: out = text.lower()
        elif args.title: out = text.title()
        else:
            w = get_words(text)
            if not w: out = ""
            elif args.camel: out = w[0].lower() + "".join(x.title() for x in w[1:])
            elif args.pascal: out = "".join(x.title() for x in w)
            elif args.snake: out = "_".join(x.lower() for x in w)
            elif args.screaming_snake: out = "_".join(x.upper() for x in w)
            elif args.kebab: out = "-".join(x.lower() for x in w)
        print(out)
    except Exception as e:
        sys.exit(f"Error: {e}")

if __name__ == "__main__":
    main()

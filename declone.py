#!/usr/bin/env python3
import argparse, sys, hashlib
from pathlib import Path
from collections import defaultdict

def get_hash(path, full=False):
    h = hashlib.blake2b()
    try:
        with open(path, 'rb') as f:
            if not full:
                h.update(f.read(4096))
            else:
                while chunk := f.read(8192): h.update(chunk)
    except OSError: return None
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser(description="Duplicate file finder.")
    p.add_argument('dirs', nargs='+', help="Directories to scan")
    p.add_argument('-d', '--delete', action='store_true', help="Interactively delete duplicates")
    args = p.parse_args()

    sizes = defaultdict(list)
    for d in args.dirs:
        root = Path(d)
        if not root.is_dir(): sys.exit(f"Error: '{d}' is not a directory.")
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                try: sizes[path.stat().st_size].append(path)
                except OSError: pass

    # Fast hash (first 4KB)
    fast = defaultdict(list)
    for group in (g for g in sizes.values() if len(g) > 1):
        for path in group:
            h = get_hash(path)
            if h: fast[h].append(path)

    # Full hash
    dupes = defaultdict(list)
    for group in (g for g in fast.values() if len(g) > 1):
        for path in group:
            h = get_hash(path, full=True)
            if h: dupes[h].append(path)

    results = [g for g in dupes.values() if len(g) > 1]

    if not results:
        print("No duplicates found.")
        return

    saved = 0
    for group in results:
        print("\nDuplicate group:")
        size = group[0].stat().st_size
        saved += size * (len(group) - 1)
        for i, path in enumerate(group): print(f"  [{i}] {path}")

    print(f"\nFound {len(results)} groups of duplicates. Wasted space: {saved / 1048576:.2f} MB")

    if args.delete:
        print("\nInteractive deletion mode:")
        for group in results:
            print("\nGroup:")
            for i, path in enumerate(group): print(f"  [{i}] {path}")
            choice = input("Enter index to KEEP (or 's' to skip) [0]: ").strip().lower()
            if choice == 's': continue
            idx = int(choice) if choice.isdigit() else 0
            for i, path in enumerate(group):
                if i != idx:
                    try:
                        path.unlink()
                        print(f"Deleted: {path}")
                    except OSError as e: print(f"Error deleting {path}: {e}")

if __name__ == "__main__": main()

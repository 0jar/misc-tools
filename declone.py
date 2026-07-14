#!/usr/bin/env python3
import argparse, sys, hashlib
from pathlib import Path
from collections import defaultdict

def get_hash(path, full=False):
    h = hashlib.blake2b()
    try:
        with open(path, 'rb') as f:
            if full:
                while chunk := f.read(8192): h.update(chunk)
            else: h.update(f.read(4096))
        return h.hexdigest()
    except OSError: return None

def main():
    p = argparse.ArgumentParser(description="Find and resolve duplicate files.")
    p.add_argument('dirs', nargs='+', type=Path, help="Directories to scan")
    p.add_argument('--min-size', type=float, default=0, help="Minimum file size in MB")
    p.add_argument('--dry-run', action='store_true', help="Show actions without modifying files")

    ag = p.add_mutually_exclusive_group()
    ag.add_argument('-d', '--delete', action='store_true', help="Interactively delete duplicates")
    ag.add_argument('--keep-oldest', action='store_true', help="Auto-keep oldest files")
    ag.add_argument('--keep-newest', action='store_true', help="Auto-keep newest files")

    lg = p.add_mutually_exclusive_group()
    lg.add_argument('--hardlink', action='store_true', help="Replace duplicates with hardlinks")
    lg.add_argument('--symlink', action='store_true', help="Replace duplicates with symlinks")
    args = p.parse_args()

    sizes = defaultdict(list)
    for d in args.dirs:
        if not d.is_dir(): sys.exit(f"Error: '{d}' is not a directory.")
        for path in d.rglob('*'):
            if path.is_file() and not path.is_symlink():
                try:
                    if (sz := path.stat().st_size) >= args.min_size * 1048576: sizes[sz].append(path)
                except OSError: pass

    dupes = []
    for g in (g for g in sizes.values() if len(g) > 1):
        fast = defaultdict(list)
        for path in g:
            if h := get_hash(path): fast[h].append(path)
        for fg in (fg for fg in fast.values() if len(fg) > 1):
            full = defaultdict(list)
            for path in fg:
                if h := get_hash(path, True): full[h].append(path)
            dupes.extend(g for g in full.values() if len(g) > 1)

    if not dupes: return print("No duplicates found.")

    saved = sum(g[0].stat().st_size * (len(g) - 1) for g in dupes)
    print(f"\nFound {len(dupes)} duplicate groups. Wasted space: {saved / 1048576:.2f} MB")

    if not (args.delete or args.keep_oldest or args.keep_newest):
        for g in dupes:
            print("\nGroup:")
            for i, p in enumerate(g): print(f"  [{i}] {p}")
        return

    for g in dupes:
        if args.keep_oldest or args.keep_newest:
            g.sort(key=lambda x: x.stat().st_mtime)
            keep = g[0] if args.keep_oldest else g[-1]
        else:
            print("\nGroup:")
            for i, p in enumerate(g): print(f"  [{i}] {p}")
            c = input("Enter index to KEEP (or 's' to skip) [0]: ").strip().lower()
            if c == 's': continue
            keep = g[int(c)] if c.isdigit() and int(c) < len(g) else g[0]

        for p in g:
            if p == keep: continue
            if args.dry_run:
                print(f"Would {'link' if args.hardlink or args.symlink else 'delete'}: {p} (kept {keep})")
                continue
            try:
                p.unlink()
                if args.hardlink: p.hardlink_to(keep); print(f"Hardlinked: {p} -> {keep}")
                elif args.symlink: p.symlink_to(keep.resolve()); print(f"Symlinked: {p} -> {keep}")
                else: print(f"Deleted: {p}")
            except OSError as e: print(f"Error processing {p}: {e}")

if __name__ == "__main__": main()

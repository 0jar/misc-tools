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
    p.add_argument('--min-size', type=float, default=0, help="Minimum file size in MB")
    p.add_argument('--dry-run', action='store_true', help="Do not modify files, just show what would happen")
    
    ag = p.add_mutually_exclusive_group()
    ag.add_argument('-d', '--delete', action='store_true', help="Interactively delete duplicates")
    ag.add_argument('--keep-oldest', action='store_true', help="Auto-keep oldest file, process rest")
    ag.add_argument('--keep-newest', action='store_true', help="Auto-keep newest file, process rest")

    lg = p.add_mutually_exclusive_group()
    lg.add_argument('--hardlink', action='store_true', help="Replace duplicates with hardlinks")
    lg.add_argument('--symlink', action='store_true', help="Replace duplicates with symlinks")
    args = p.parse_args()

    sizes = defaultdict(list)
    for d in args.dirs:
        root = Path(d)
        if not root.is_dir(): sys.exit(f"Error: '{d}' is not a directory.")
        for path in root.rglob('*'):
            if path.is_file() and not path.is_symlink():
                try: 
                    st = path.stat()
                    if st.st_size >= args.min_size * 1048576:
                        sizes[st.st_size].append(path)
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

    if args.delete or args.keep_oldest or args.keep_newest:
        for group in results:
            if args.keep_oldest or args.keep_newest:
                group.sort(key=lambda x: x.stat().st_mtime)
                keep_path = group[0] if args.keep_oldest else group[-1]
            else:
                print("\nGroup:")
                for i, path in enumerate(group): print(f"  [{i}] {path}")
                choice = input("Enter index to KEEP (or 's' to skip) [0]: ").strip().lower()
                if choice == 's': continue
                idx = int(choice) if choice.isdigit() and int(choice) < len(group) else 0
                keep_path = group[idx]

            for path in group:
                if path != keep_path:
                    if args.dry_run:
                        action = "Would link" if (args.hardlink or args.symlink) else "Would delete"
                        print(f"{action}: {path} (kept {keep_path})")
                        continue
                    try:
                        path.unlink()
                        if args.hardlink:
                            path.hardlink_to(keep_path)
                            print(f"Hardlinked: {path} -> {keep_path}")
                        elif args.symlink:
                            path.symlink_to(keep_path.resolve())
                            print(f"Symlinked: {path} -> {keep_path}")
                        else:
                            print(f"Deleted: {path}")
                    except OSError as e: print(f"Error processing {path}: {e}")

if __name__ == "__main__": main()

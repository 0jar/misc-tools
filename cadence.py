#!/usr/bin/env python3

import argparse
import concurrent.futures
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import unicodedata
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Set

try:
    import mutagen
    import mutagen.easyid3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

MUSIC_EXTS: Set[str] = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.alac'}
SYNC_EXTS: Set[str] = MUSIC_EXTS | {'.lrc'}
ART_NAMES: Set[str] = {'cover', 'folder', 'albumart', 'front'}
ART_EXTS: Set[str] = {'.jpg', '.jpeg', '.png', '.bmp'}

class AppState:
    def __init__(self):
        self.print_lock = threading.Lock()
        self.cache_lock = threading.Lock()
        self.cancel = threading.Event()
        self.worker_states: Dict[str, str] = {}
        self.num_lines = 0
        self.cache: Dict[str, dict] = {}
        self.cache_path: Optional[Path] = None
        self.verbose = False
        self.config = {
            "filename_parts": ["artist", "album", "track", "title"],
            "folders_parts": ["track", "title"],
            "separator": " - ",
            "album_year_format": "{album} ({year})",
            "unknown_artist": "Unknown Artist",
            "unknown_album": "Unknown Album"
        }

app = AppState()

def clear_progress() -> None:
    with app.print_lock:
        if app.num_lines > 0:
            sys.stdout.write(f"\033[{app.num_lines}A")
            sys.stdout.write("\033[K\n" * app.num_lines)
            sys.stdout.write(f"\033[{app.num_lines}A")
            sys.stdout.flush()
            app.num_lines = 0

def update_status(msg: str) -> None:
    wid = threading.current_thread().name
    with app.print_lock:
        app.worker_states[wid] = msg
        if app.num_lines > 0:
            sys.stdout.write(f"\033[{app.num_lines}A")

        lines = [f"\033[KWorker {k.split('-')[-1].zfill(2)}: {app.worker_states[k]}"
                 for k in sorted(app.worker_states)]

        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        app.num_lines = len(lines)

def print_progress(i: int, total: int, file_type: str, safe_name: str) -> None:
    update_status(f"[{i}/{total}] Processing {file_type}: {safe_name[:60]}")

def log_error(msg: str, exc: Exception = None) -> None:
    clear_progress()
    full_msg = f"{msg}\nDetail: {exc}" if exc else msg
    with app.print_lock:
        print(full_msg)
    logging.error(f"{msg}: {exc}" if exc else msg)

def verbose_log(msg: str) -> None:
    if app.verbose:
        clear_progress()
        with app.print_lock:
            print(f"[VERBOSE] {msg}")
        logging.debug(msg)

def load_settings(root: Path) -> None:
    config_path = root / ".organise_config.json"
    if config_path.is_file():
        try:
            app.config.update(json.loads(config_path.read_text(encoding="utf-8")))
            logging.info("Loaded custom config.")
        except Exception as e:
            log_error("Failed to load config", e)

    app.cache_path = root / ".music_cache.json"
    if app.cache_path.is_file():
        try:
            app.cache = json.loads(app.cache_path.read_text(encoding="utf-8"))
            logging.info(f"Loaded {len(app.cache)} cache entries.")
        except Exception as e:
            log_error("Failed to load cache", e)

def save_cache() -> None:
    if app.cache_path:
        try:
            app.cache_path.write_text(json.dumps(app.cache, indent=2), encoding="utf-8")
        except Exception as e:
            log_error("Failed to save cache", e)

def get_metadata(path: Path) -> dict:
    try:
        stat = path.stat()
        key = f"{path.resolve()}_{stat.st_mtime}_{stat.st_size}"
    except OSError:
        key = str(path.resolve())

    with app.cache_lock:
        if key in app.cache:
            return app.cache[key]

    tags = {}

    if HAS_MUTAGEN:
        try:
            if path.suffix.lower() == '.mp3':
                try:
                    audio = mutagen.easyid3.EasyID3(path)
                except Exception:
                    audio = mutagen.File(path)
            else:
                audio = mutagen.File(path)

            if audio is not None:
                for k, v in audio.items():
                    val = str(v[0]) if isinstance(v, list) and v else str(v)
                    k_lower = k.lower().replace('\xa9', '')
                    if k_lower == 'trkn' and isinstance(v, list) and v and isinstance(v[0], tuple):
                        val = str(v[0][0])
                    tag_map = {'nam':'title', 'alb':'album', 'art':'artist', 'day':'date', 'trk':'track', 'trkn':'track', 'tracknumber':'track'}
                    k_lower = tag_map.get(k_lower, k_lower)

                    tags[k_lower] = val.strip()

                with app.cache_lock:
                    app.cache[key] = tags
                return tags
        except Exception as e:
            verbose_log(f"mutagen failed for {path.name}: {e}. Falling back to ffprobe.")

    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        tags = {k.lower(): str(v).strip() for k, v in json.loads(res.stdout).get('format', {}).get('tags', {}).items()}
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        verbose_log(f"ffprobe failed for {path.name}: {e}")

    with app.cache_lock:
        app.cache[key] = tags
    return tags

def sanitize(name: str) -> str:
    return unicodedata.normalize('NFC', "".join('_' if c in '/\\?%*:|"<>' else c for c in name)).strip(" .")

def get_unique_path(dest: Path, basename: str, ext: str, skip: Path = None) -> Path:
    target = dest / f"{basename}{ext}"
    if not target.exists() or (skip and target.exists() and target.samefile(skip)):
        return target
    i = 1
    while True:
        test = dest / f"{basename}_{i}{ext}"
        if not test.exists() or (skip and test.exists() and test.samefile(skip)):
            return test
        i += 1

def move_file(src: Path, dest: Path, dry_run: bool, log_msg: str) -> None:
    if src == dest or (dest.exists() and src.samefile(dest)):
        return
    full_msg = f"{'[DRY-RUN] ' if dry_run else ''}{log_msg}"
    logging.info(full_msg)
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

def process_file(path: Path, root: Path, mode: str, dry_run: bool, i: int, total: int) -> None:
    if app.cancel.is_set() or not path.exists():
        return

    ext = path.suffix.lower()
    basename = sanitize(path.stem)
    safe_name = "".join(c for c in path.name if c.isprintable())
    print_progress(i, total, "Music" if ext in MUSIC_EXTS else "Lyrics", safe_name)

    dest_dir = root
    art_targets = []

    if ext in MUSIC_EXTS:
        tags = get_metadata(path)
        artist = sanitize(tags.get('artist') or tags.get('album_artist') or tags.get('albumartist') or "")
        album = sanitize(tags.get('album') or "")
        title = sanitize(tags.get('title') or "")
        date = tags.get('date') or tags.get('year') or tags.get('originaldate')
        year = str(date)[:4] if date else ""
        track = sanitize((tags.get('track') or "").split('/')[0].strip())

        if not title:
            verbose_log(f"Missing title metadata for {path.name}, skipping renaming.")

        if title:
            fields = {
                "artist": artist or app.config["unknown_artist"],
                "album": album or app.config["unknown_album"],
                "track": track,
                "title": title
            }

            if mode == "folders":
                final_album = fields["album"]
                if year and final_album != app.config["unknown_album"]:
                    final_album = app.config["album_year_format"].format(album=final_album, year=year)
                dest_dir = root / fields["artist"] / final_album
                parts = [fields.get(p) for p in app.config["folders_parts"] if fields.get(p)]
            else:
                parts = [fields.get(p) for p in app.config["filename_parts"] if fields.get(p)]

            if parts:
                basename = app.config["separator"].join(parts)

            art_targets = [path.parent / f"{n}{e}" for n in ART_NAMES for e in ART_EXTS if (path.parent / f"{n}{e}").is_file()]

    try:
        dest = get_unique_path(dest_dir, basename, ext, skip=path)
        if path.parent == dest.parent and path.name.lower() == dest.name.lower() and path.name != dest.name:
            dest = get_unique_path(dest_dir, f"{basename}_new", ext, skip=path)

        move_file(path, dest, dry_run, f"[{i}/{total}] {path.name} -> {dest.name}")

        if ext in MUSIC_EXTS:
            old_lrc = path.with_suffix('.lrc')
            if old_lrc.exists():
                print_progress(i, total, "Lyrics", "".join(c for c in old_lrc.name if c.isprintable()))
                move_file(old_lrc, dest.with_suffix('.lrc'), dry_run, f"[{i}/{total}] + lyrics: {dest.with_suffix('.lrc').name}")

            for art in set(art_targets):
                print_progress(i, total, "Album Art", "".join(c for c in art.name if c.isprintable()))
                if mode == "folders":
                    new_art = get_unique_path(dest_dir, art.stem, art.suffix, skip=art)
                else:
                    base = f"{artist} - {album}" if (artist and album) else art.stem
                    new_art = get_unique_path(dest_dir, base, art.suffix, skip=art)
                move_file(art, new_art, dry_run, f"[{i}/{total}] + artwork: {new_art.name}")

    except PermissionError as e:
        log_error(f"Permission denied (file locked?): {path.name}", e)
    except OSError as e:
        log_error(f"OS error processing {path.name}", e)
    except Exception as e:
        log_error(f"Error processing {path.name}", e)

def auto_detect_mode(root: Path) -> str:
    subfolders = [d for d in root.iterdir() if d.is_dir() and d.name.lower() not in ('.thumbnails')]
    if not subfolders:
        return "filename"
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in MUSIC_EXTS and path.parent != root:
            artist = sanitize(get_metadata(path).get('artist', '')).lower()
            if artist and any(sanitize(p).lower() == artist for p in path.relative_to(root).parts[:-1]):
                return "folders"
    return "unknown"

def organise_music(root: Path, mode: str, dry_run: bool, clean: bool, workers: int, log_path: Path) -> None:
    if not root.is_dir():
        log_error(f"Directory not found: {root}")
        return

    print(f"Scanning {root} for audio files...")
    logging.info(f"Scanning {root}...")
    load_settings(root)

    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SYNC_EXTS]
    total = len(files)
    print(f"Found {total} files. Starting {'[DRY-RUN] ' if dry_run else ''}with {workers} workers...\nLogs: {log_path}\n")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    try:
        futures = [executor.submit(process_file, p, root, mode, dry_run, i, total) for i, p in enumerate(files, 1)]
        while futures and not all(f.done() for f in futures):
            concurrent.futures.wait(futures, timeout=0.5)
    except KeyboardInterrupt:
        clear_progress()
        print("\nCancellation requested via Ctrl+C. Waiting for active threads to finish...")
        app.cancel.set()
        for f in futures: f.cancel()
    finally:
        executor.shutdown(wait=True)

    clear_progress()
    save_cache()
    print("\nFile processing complete.")

    if clean:
        print("Cleaning up empty directories...")
        empty_count = 0
        for dir_path, dirnames, filenames in os.walk(root, topdown=False):
            dp = Path(dir_path)
            if dp != root and not any(dp.iterdir()):
                try:
                    if not dry_run: dp.rmdir()
                    logging.info(f"{'[DRY-RUN] ' if dry_run else ''}Removed empty: {dp}")
                    empty_count += 1
                except OSError as e:
                    logging.error(f"Could not remove {dp}: {e}")
        print(f"Removed {empty_count} empty directories.")
    print("Done!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Organise music directories and rename files using ffprobe metadata.")
    parser.add_argument("directory", type=Path, help="Root music directory.")
    parser.add_argument("--mode", choices=["filename", "folders"], help="Specify sorting mode.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate processing without modifying files.")
    parser.add_argument("--no-clean", action="store_true", help="Do not delete empty directories.")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent workers. Default is 4. More workers may speed up the process but will use more system resources.")
    parser.add_argument("--log-dir", type=Path, help="Custom directory to save organise_music.log.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    args = parser.parse_args()

    if not HAS_MUTAGEN:
        print("Note: 'mutagen' is not installed. Falling back to ffprobe for metadata extraction.")
        print("Install 'mutagen' for faster performance: 'python3 -m pip install mutagen'.\n")

    if shutil.which("ffprobe") is None:
        print("Error: 'ffprobe' is not installed or not in PATH.")
        print("Please install ffmpeg to use this tool.")
        sys.exit(1)

    app.verbose = args.verbose

    log_path = args.log_dir.resolve() / 'organise_music.log' if args.log_dir else Path('organise_music.log').resolve()
    if args.log_dir:
        args.log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=str(log_path), level=logging.DEBUG if app.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s", filemode='w'
    )

    mode = args.mode
    root = args.directory.resolve()

    if mode not in ("filename", "folders"):
        print("Analysing directory structure...")
        mode = auto_detect_mode(root)
        if mode == "filename":
            print("Detected no subfolders. Suggested mode: sort by filename (Artist - Album - ## - Title.ext)")
            mode = "filename" if input("Proceed? [Y/n]: ").strip().lower() in ("","y","yes") else ""
        elif mode == "folders":
            print("Detected nested subfolders. Suggested mode: sort by subfolders (/Artist/Album (Year)/## - Title.ext)")
            mode = "folders" if input("Proceed? [Y/n]: ").strip().lower() in ("","y","yes") else ""

    while mode not in ("filename", "folders"):
        print("\nChoose organisation mode:\n[1] Sort by filename\n[2] Sort by subfolders")
        mode = {"1": "filename", "2": "folders"}.get(input("Enter 1 or 2: ").strip(), "")

    organise_music(root, mode, args.dry_run, not args.no_clean, args.workers, log_path)

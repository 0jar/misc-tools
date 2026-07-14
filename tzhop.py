#!/usr/bin/env python3
import sys
from datetime import datetime, timezone, timedelta

try: from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError: sys.exit("Requires Python 3.9+.")

POPULAR = [
    'UTC', 'America/New_York', 'America/Chicago', 'America/Los_Angeles', 'America/Sao_Paulo',
    'Europe/London', 'Europe/Paris', 'Europe/Helsinki', 'Europe/Moscow',
    'Asia/Kolkata', 'Asia/Jakarta', 'Asia/Shanghai', 'Asia/Tokyo', 'Australia/Sydney'
]

def get_tz(s):
    try: return ZoneInfo(s)
    except ZoneInfoNotFoundError: pass

    u = s.upper().replace('UTC', '').replace('GMT', '')
    if not u or u[0] not in '+-': return None

    try:
        sign = 1 if u[0] == '+' else -1
        u = u[1:].replace(':', '')
        h, m = (int(u[:-2]), int(u[-2:])) if len(u) >= 3 else (int(u), 0)
        return timezone(timedelta(hours=h*sign, minutes=m*sign), s)
    except ValueError:
        return None

def main():
    args = sys.argv[1:]
    if '-h' in args or '--help' in args or len(args) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <time> <from_tz> [to_tz...]\nExample: {sys.argv[0]} 2026-05-27 10:00 UTC+7 Europe/Tallinn -05:00")
    t = args.pop(0)
    if args and len(t) == 10 and t.count('-') == 2 and ':' in args[0]:
        t += 'T' + args.pop(0)
    if not args: sys.exit("Error: Missing source timezone.")
    from_tz = args.pop(0)
    zi = get_tz(from_tz)
    if not zi: sys.exit(f"Error: Unknown timezone '{from_tz}'")

    t = t.replace(' ', 'T')
    if 'T' not in t and '-' not in t:
        t = f"{datetime.now(zi).date()}T{t}"

    try:
        dt = datetime.fromisoformat(t)
        dt = dt.replace(tzinfo=zi) if dt.tzinfo is None else dt.astimezone(zi)
    except ValueError as e:
        sys.exit(f"Error parsing time: {e}")

    print(f"[{dt.strftime('%Y-%m-%d %H:%M:%S %Z')}] {from_tz}\n" + "-" * 50)

    for tz in (args or POPULAR):
        tzi = get_tz(tz)
        print(f"{tz:<25} {dt.astimezone(tzi).strftime('%Y-%m-%d %H:%M:%S %Z') if tzi else '(Unknown timezone)'}")

if __name__ == "__main__":
    main()

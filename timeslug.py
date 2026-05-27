#!/usr/bin/env python3
import sys
from datetime import datetime, timezone

def encode_base36(n: int) -> str:
    res = ""
    while n:
        n, i = divmod(n, 36)
        res = "0123456789abcdefghijklmnopqrstuvwxyz"[i] + res
    return res or "0"

def generate_code(iso_datetime: str, offset: int = 10957) -> str:
    dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError("Timezone must be specified in the datetime string")
    a = int(dt.timestamp() // 86400) - offset
    if a < 0:
        raise ValueError("Date is before epoch offset")
    dt_utc = dt.astimezone(timezone.utc)
    t = dt_utc.hour * 60 + dt_utc.minute
    return f"{encode_base36(a).zfill(3)}{encode_base36(t).zfill(3)}"

if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        print(f"Usage: {sys.argv[0]} <iso_datetime> [optional_offset]\nGenerate a short base36 code from an ISO 8601 datetime string (YYYY-MM-DDTHH:MM:SS[+/-TZ]).\nOffset is number of days to add to the epoch start date (1970-01-01). Default is 10957 (30 years).")
        sys.exit(0)
    if not (2 <= len(sys.argv) <= 3):
        sys.exit(f"Usage: {sys.argv[0]} <iso_datetime> [optional_offset]")
    try:
        iso_str = sys.argv[1]
        dt_check = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        if dt_check.tzinfo is None:
            print("No timezone provided. Please choose an option:")
            print("1. Use system timezone")
            print("2. Use UTC")
            print("3. Input custom timezone (e.g., +07:00)")
            choice = input("Choice (1/2/3): ").strip()
            if choice == '1':
                iso_str = dt_check.astimezone().isoformat()
            elif choice == '2':
                iso_str = dt_check.replace(tzinfo=timezone.utc).isoformat()
            elif choice == '3':
                tz = input("Enter timezone offset (e.g. +02:00): ").strip()
                iso_str = dt_check.isoformat() + tz
            else:
                sys.exit("Error: Invalid choice.")

        custom_offset = int(sys.argv[2]) if len(sys.argv) == 3 else 10957
        print(generate_code(iso_str, custom_offset))
    except Exception as e:
        sys.exit(f"Error: {e}")

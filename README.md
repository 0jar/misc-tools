# misc-tools

Jarema's collection of miscellaneous utility scripts.

## Tools

### 1. timeslug.py

Slugs an ISO 8601 datetime string into a base36 code.

**Usage:**

```bash
./timeslug.py <iso_datetime> [optional_offset]
```

- `<iso_datetime>`: An ISO 8601 formatted datetime string (e.g., `2050-05-20T06:06:25+02:00`). If the timezone is omitted, the script will prompt you to choose between system timezone, UTC, or a custom offset.
- `[optional_offset]`: (Optional) The number of days to add to the epoch start date (1970-01-01). Default is `10957` (30 years).

**Example:**

```bash
$ ./timeslug.py 2050-05-20T06:06:25+02:00
e7606u
```

### 2. namescout.py

Scouts username availability across various platforms (GitHub, GitLab, Reddit, Twitter, Hacker News and more).

**Usage:**

```bash
./namescout.py -i <input_file> [options]
```

- `-i`, `--input`: (Required) File containing a list of usernames to check (one per line).
- `-o`, `--out`: (Optional) Output file to save available usernames (default: `avail.txt`).
- `-b`, `--bl`: (Optional) Blacklist file containing usernames to skip (one per line).
- `--all`: Check availability across all supported services.
- `--<service_name>`: Check a specific service (e.g., `--github`, `--twitter`, `--reddit`).
- `-c`, `--custom`: Use a custom service URL. Use `{}` as a placeholder for the username (e.g., `https://example.com/user/{}`).

**Example:**

```bash
$ ./namescout.py -i usernames.txt --github --gitlab --twitter
```

### 3. linkprobe.py

Checks/probes a list of URLs and reports which ones 404, redirect chains or timeout.

**Usage:**

```bash
./linkprobe.py [urls...] -f <input_file> [options]
```

- `urls`: List of URLs to check directly.
- `-f`, `--file`: Local file containing URLs (one per line).
- `-w`, `--workers`: Number of concurrent workers (default: 10).

**Example:**

```bash
$ ./linkprobe.py https://jarema.me/blank https://example.com/dead
```

```bash
$ ./linkprobe.py -f my_links.txt -w 10
```

### 4. headhunt.py

Hunts down metadata from a webpage's <head>: the page title, description, Open Graph tags, canonical URL, microformats (JSON-LD and h-card tags).

**Usage:**

```bash
./headhunt.py <url>
```

- `<url>`: The URL to fetch and extract metadata from.

**Example:**

```bash
$ ./headhunt.py https://jarema.me/
```

### 5. clockshift.py

Shifts a given time across multiple timezones.

**Usage:**

```bash
./clockshift.py <time> <from_tz> [to_tzs...]
```

- `<time>`: The time string to convert. Can be an ISO 8601 string (e.g., `2050-05-20T06:06:25`), a space-separated date and time (e.g., `2050-05-20 06:06`), or just a time (e.g., `06:06:25`).
- `<from_tz>`: The source timezone (e.g. `UTC+7`, `Europe/Tallinn`, `-04:00`).
- `[to_tzs...]`: (Optional) One or more target timezones. If none are provided, the script will output the converted time in a default list of popular timezones.

**Example:**

```bash
$ ./clockshift.py 2050-05-20 06:06:25 Europe/Tallinn UTC+7 -05:00
[2050-05-20 06:06:25 EEST] Europe/Tallinn
--------------------------------------------------
UTC+7                     2050-05-20 10:06:25 UTC+7
-05:00                    2050-05-19 22:06:25 -05:00
```

```bash
$ ./clockshift.py 2050-05-20 06:06:25 UTC+7
[2050-05-20 06:06:25 UTC+7] UTC+7
--------------------------------------------------
UTC                       2050-05-19 23:06:25 UTC
America/New_York          2050-05-19 19:06:25 EDT
America/Chicago           2050-05-19 18:06:25 CDT
America/Los_Angeles       2050-05-19 16:06:25 PDT
America/Sao_Paulo         2050-05-19 20:06:25 -03
Europe/London             2050-05-20 00:06:25 BST
Europe/Paris              2050-05-20 01:06:25 CEST
Europe/Helsinki           2050-05-20 02:06:25 EEST
Europe/Moscow             2050-05-20 02:06:25 MSK
Asia/Kolkata              2050-05-20 04:36:25 IST
Asia/Jakarta              2050-05-20 06:06:25 WIB
Asia/Shanghai             2050-05-20 07:06:25 CST
Asia/Tokyo                2050-05-20 08:06:25 JST
Australia/Sydney          2050-05-20 09:06:25 AEST
```

### 6. tunesort.py

Sorts your tunes (music files) in your music library cleanly.

**Usage:**

```bash
./tunesort.py [TARGET_DIRECTORY] [options]
```

- `TARGET_DIRECTORY`: The directory containing music files.
- `--workers <N>`: (Optional) Number of concurrent threads to use (default: 4).
- `--no-clean`: (Optional) Skips cleaning up empty directories after organising.
- `--log-dir <DIR>`: (Optional) Specify a custom directory to store the log file.
- `--verbose`: (Optional) Enable verbose output in the CLI.

**Example:**

```bash
$ ./tunesort.py ~/Muusika --workers 16 --no-clean --verbose
```

## License

Do whatever you want with this code. License is [WTFPL](LICENSE).

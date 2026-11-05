# Juliana's desk display

Two protected server-rendered pages: `/status` mirrors one Notion page; `/clock`
(also `/`) shows New York time, English date and a Sunday-first month calendar.
Python 3.9+ with system timezone data; the supplied image uses Python 3.12.
No packages, JavaScript, external fonts or browser API dependencies.

## Configure

Create a Notion internal integration with **read content** capability only. Share
only the Status page with it. Do not grant workspace-wide access. Obtain its
token and the page ID from the page URL (32 hexadecimal characters, optionally
hyphenated). Use the page ID, not the whole URL.

Set these server environment variables in the host's secret settings:

| Variable | Value |
| --- | --- |
| `NOTION_TOKEN` | Internal integration token |
| `NOTION_PAGE_ID` | Exact Status page ID |
| `DISPLAY_USER` | ASCII username, e.g. juliana |
| `DISPLAY_PASSWORD` | Random ASCII password, at least 20 characters |
| `STATUS_REFRESH_SECONDS` | Optional, 60–300; default 180 |
| `PORT` | Optional, default 8080 |

Generate a password locally with `python -c 'import secrets; print(secrets.token_urlsafe(32))'`.
Store it in a password manager. Never commit `.env` or put credentials into URLs.
Startup fails if required configuration is missing. Both pages, including `/`,
require the same HTTP Basic credentials. Authentication happens before Notion is
read. The Notion token never appears in HTML or request logs.

## Cloud deployment

Deploy this directory as a Docker web service on Render or another host supporting
an always-running container, secret environment variables and managed HTTPS.
For Render: create a Web Service from a private repository containing these files,
choose Docker, set the variables above, and select an always-on instance (avoid
free services that sleep). Use the service's HTTPS URL. No volume is needed.
If the host has a health check, use a TCP check; every HTTP route is protected.
The process serves HTTP internally; the hosting proxy **must enforce HTTPS** on
the public side. Basic authentication is unsafe over public plain HTTP.

No hosting account or Notion credentials were provided with this build, so it is
not deployed yet. Actual Notion access and the iPad test remain required.

For local checks only, set environment variables and run `python app.py`.
Run automated tests with `python -m unittest -v`.

## Rendering and freshness

Status fetches the page title and all paginated child blocks, recursively, using
the official read-only Notion API. It preserves text, text emphasis, headings,
list numbering, nested lists, checkboxes, tables, quotes, callouts and expanded
toggle content. Columns stack vertically for readability. External links display
as text; images, embeds, databases, child pages and other unsupported blocks show
an explicit block marker. It does not traverse child pages or query databases.
Check the actual Status page before declaring content parity; unsupported blocks
may require a renderer extension. Nested blocks are limited to 30 levels.

Successful Status output is cached in memory for the configured refresh interval.
The browser refreshes at that interval, so a change may take up to about twice
the interval to appear around a cache boundary. A failed read displays a retry
message instead of presenting old content as current. Clock refreshes every 60
seconds relative to page load, so its displayed minute can lag by up to a minute.
New York daylight saving changes use the server's IANA timezone database.

## Olivia's acceptance checklist

- Open the HTTPS URL in a fresh private tab: both pages must prompt for credentials;
  test missing and wrong credentials. Do not embed credentials in bookmarks.
- On the actual iPad Air / iOS 12.5.8, sign in and open `/status`. Compare every
  section and item with Notion, including long text, lists and any special blocks.
- Edit Status on the phone/Mac; wait up to two refresh intervals and confirm it
  updates without touching the iPad. Remove integration access and confirm a
  retry message replaces Status on the next uncached refresh; restore access.
- Check `/clock` against New York time and date, the month layout, today's highlight,
  and automatic minute refresh. Test both portrait and landscape; adjust iPad text
  zoom if needed. Follow each cross-link and confirm authentication persists.
- Set Settings → Display & Brightness → Auto-Lock → Never if available, connect
  power, lower brightness, and bookmark the clock. The website cannot prevent
  iOS from sleeping or automatically switch pages.

Automated checks cover authentication, escaping, pagination, cache/error behavior,
cross-links, refresh tags, DST and leap-day calendar output. They do not prove
iOS 12 Safari rendering; the physical-device check is still required.

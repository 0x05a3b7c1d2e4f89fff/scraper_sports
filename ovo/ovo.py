import asyncio
import re
import urllib.parse
from functools import partial
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from utils import Cache, Time, get_logger, leagues, network

log = get_logger(__name__)

urls: dict[str, dict[str, str | float]] = {}

TAG = "VOLOKIT"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"

CACHE_FILE = Cache(TAG, exp=10_800)
HTML_CACHE = Cache(f"{TAG}-html", exp=3600)

BASE_URL = "http://volokit.xyz"
SCHEDULE_URL = "http://volokit.xyz/schedule"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) "
    "Gecko/20100101 Firefox/147.0"
)

# =========================
# PLAYLIST GENERATOR
# =========================

def _format_extinf(key: str, entry: dict) -> str:
    tvg_id = entry.get("id", "")
    logo = entry.get("logo", "")
    group = entry.get("sport", "Live")

    return (
        f'#EXTINF:-1 tvg-id="{tvg_id}" '
        f'tvg-logo="{logo}" '
        f'group-title="{group}",{key}'
    )


def generate_vlc_playlist(urls: dict, output_file="ovo_vlc.m3u8"):
    lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']

    for key, entry in sorted(urls.items()):
        stream_url = entry.get("url")
        if not stream_url:
            continue

        lines.append(_format_extinf(key, entry))
        lines.append(f"#EXTVLCOPT:http-referrer={BASE_URL}/")
        lines.append(f"#EXTVLCOPT:http-origin={BASE_URL}")
        lines.append(f"#EXTVLCOPT:http-user-agent={USER_AGENT}")
        lines.append(stream_url)
        lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_tivimate_playlist(urls: dict, output_file="ovo_tivimate.m3u8"):
    encoded_ua = urllib.parse.quote(USER_AGENT, safe="")

    lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']

    for key, entry in sorted(urls.items()):
        stream_url = entry.get("url")
        if not stream_url:
            continue

        lines.append(_format_extinf(key, entry))

        header_string = (
            f"{stream_url}|"
            f"referer={BASE_URL}/&"
            f"origin={BASE_URL}&"
            f"user-agent={encoded_ua}"
        )

        lines.append(header_string)
        lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_all_playlists(urls: dict):
    generate_vlc_playlist(urls)
    generate_tivimate_playlist(urls)


# =========================
# SCRAPER LOGIC
# =========================

def fix_event(s: str) -> str:
    return " ".join(x.capitalize() for x in s.split())


async def process_event(url: str, url_num: int) -> str | None:
    if not (event_data := await network.request(url, log=log)):
        log.info(f"URL {url_num}) Failed to load url.")
        return

    soup = HTMLParser(event_data.content)

    if not (iframe := soup.css_first('iframe[height="100%"]')):
        log.warning(f"URL {url_num}) No iframe element found.")
        return

    if not (iframe_src := iframe.attributes.get("src")):
        log.warning(f"URL {url_num}) No iframe source found.")
        return

    if not (
        iframe_src_data := await network.request(
            iframe_src,
            headers={"Referer": url},
            log=log,
        )
    ):
        log.info(f"URL {url_num}) Failed to load iframe source.")
        return

    pattern = re.compile(r'source:\s+"([^"]*)"', re.I)

    if not (match := pattern.search(iframe_src_data.text)):
        log.warning(f"URL {url_num}) No source found.")
        return

    log.info(f"URL {url_num}) Captured M3U8")

    return match[1]


async def get_events(cached_keys):
    now = Time.clean(Time.now())
    events = {}

    if not (html_data := await network.request(SCHEDULE_URL, log=log)):
        log.error("Failed to fetch schedule page.")
        return []

    soup = HTMLParser(html_data.content)
    
    current_date = now.date()

    # Volokit schedule uses rows (tr) within the main table
    rows = soup.css("tr")
    log.info(f"Analyzing {len(rows)} rows on schedule page...")

    for row in rows:
        # 1. Update Date
        if "date" in (row.attributes.get("class") or ""):
            current_date = row.text(strip=True).replace(",", "")
            continue
            
        # 2. Extract Event Data
        link_node = row.css_first("a")
        time_node = row.css_first(".time")
        
        if not link_node or not time_node:
            continue
            
        href = link_node.attributes.get("href")
        if not href or href == "/":
            continue

        name = link_node.text(strip=True).replace("@", "vs")
        time_str = time_node.text(strip=True)
        
        # Determine Sport from URL slug
        sport_match = re.search(r'/sport/([^/]+)/', href)
        sport_slug = sport_match.group(1).upper() if sport_match else "LIVE"

        event_name = fix_event(name)
        
        # Construct Timestamp
        try:
            event_dt = Time.from_str(f"{current_date} {time_str}", timezone="UTC")
            ts = event_dt.timestamp()
        except Exception:
            ts = now.timestamp()
        
        full_link = urljoin(BASE_URL, href)
        key = f"[{sport_slug}] {event_name} ({TAG})"
        
        # Only process if URL isn't already valid in cache
        if key not in cached_keys or not cached_keys[key].get("url"):
            events[key] = {
                "sport": sport_slug,
                "event": event_name,
                "link": full_link,
                "event_ts": ts,
                "timestamp": now.timestamp(),
            }

    return list(events.values())


async def scrape() -> None:
    cached_urls = CACHE_FILE.load()
    
    # Keep track of what we already have working
    urls.update({k: v for k, v in cached_urls.items() if v.get("url")})
    
    log.info(f"Loaded {len(urls)} existing active stream(s) from cache")
    log.info(f'Scraping: "{SCHEDULE_URL}"')

    events = await get_events(cached_urls)

    if events:
        log.info(f"Found {len(events)} new/expired events to process")

        for i, ev in enumerate(events, start=1):
            handler = partial(
                process_event,
                url=(link := ev["link"]),
                url_num=i,
            )

            # Extract the actual stream URL
            m3u8_link = await network.safe_process(
                handler,
                url_num=i,
                semaphore=network.HTTP_S,
                log=log,
            )

            sport, event, ts = ev["sport"], ev["event"], ev["event_ts"]
            key = f"[{sport}] {event} ({TAG})"

            tvg_id, logo = leagues.get_tvg_info(sport, event)

            entry = {
                "url": m3u8_link,
                "logo": logo,
                "base": link,
                "timestamp": ts,
                "id": tvg_id or "Live.Event.us",
                "link": link,
                "sport": sport,
            }

            cached_urls[key] = entry
            if m3u8_link:
                urls[key] = entry

    # Create the m3u8 files
    generate_all_playlists(urls)
    log.info(f"Done. Generated playlists with {len(urls)} streams.")
    
    CACHE_FILE.write(cached_urls)

if __name__ == "__main__":
    asyncio.run(scrape())

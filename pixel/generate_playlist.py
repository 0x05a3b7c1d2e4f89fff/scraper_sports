import json
import cloudscraper
import os
from datetime import datetime, timedelta

# Configuration
BASE = "https://pixelsport.tv"
JSON_URL = f"{BASE}/backend/liveTV/events"
USERNAME = "BuddyChewChew"
REPO = "sports"
SUBDIR = "pixel"
LOCAL_JSON = f"{SUBDIR}/events.json"
XML_URL = f"https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/{SUBDIR}/epg.xml"

def generate_files():
    # Initialize cloudscraper to bypass Cloudflare
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'firefox',
            'platform': 'windows',
            'desktop': True
        }
    )

    data = None

    try:
        print(f"Attempting live fetch from {JSON_URL}...")
        response = scraper.get(JSON_URL, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # Save the fresh data for next time/records
        os.makedirs(SUBDIR, exist_ok=True)
        with open(LOCAL_JSON, 'w') as f:
            json.dump(data, f, indent=4)
        print("Live fetch successful.")

    except Exception as e:
        print(f"Live fetch failed: {e}")
        if os.path.exists(LOCAL_JSON):
            print("Falling back to local events.json...")
            with open(LOCAL_JSON, 'r') as f:
                data = json.load(f)
        else:
            print("No local backup found. Exiting.")
            return

    # Generation Logic
    m3u_lines = [f'#EXTM3U x-tvg-url="{XML_URL}"']
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE tv SYSTEM "xmltv.dtd">',
        '<tv generator-info-name="BuddyChewChew-Cloud-Gen">'
    ]

    for event in data.get('events', []):
        ch = event.get('channel', {})
        ch_id = ch.get('_id')
        if not ch_id: continue
            
        tv_name = ch.get('TVName', 'Unknown Channel')
        sport = event.get('sport', 'Sports')
        logo = event.get('away_logo', '')
        
        # M3U Entry
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{sport}",{tv_name}')
        m3u_lines.append(f"{BASE}/live/{ch_id}.m3u8")

        # EPG Entry
        try:
            # Parse date: 2026-03-10T02:00:00.000Z
            start_dt = datetime.strptime(event.get('date'), '%Y-%m-%dT%H:%M:%S.%fZ')
            xml_start = start_dt.strftime('%Y%m%d%H%M%S +0000')
            xml_stop = (start_dt + timedelta(hours=3)).strftime('%Y%m%d%H%M%S +0000')
        except: continue

        xml_lines.append(f'  <channel id="{ch_id}"><display-name>{tv_name}</display-name></channel>')
        xml_lines.append(f'  <programme start="{xml_start}" stop="{xml_stop}" channel="{ch_id}">')
        xml_lines.append(f'    <title lang="en">{event.get("matchName")}</title>')
        xml_lines.append(f'    <desc lang="en">Status: {event.get("gameStatusDetail")} | {event.get("location")}</desc>')
        xml_lines.append(f'    <category lang="en">{sport}</category>')
        xml_lines.append(f'    <icon src="{logo}" />')
        xml_lines.append(f'  </programme>')

    xml_lines.append('</tv>')

    with open(f"{SUBDIR}/playlist.m3u8", 'w') as f:
        f.write('\n'.join(m3u_lines))
    with open(f"{SUBDIR}/epg.xml", 'w') as f:
        f.write('\n'.join(xml_lines))
    print("Files updated successfully.")

if __name__ == "__main__":
    generate_files()

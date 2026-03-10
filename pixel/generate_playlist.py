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
XML_URL = f"https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/{SUBDIR}/epg.xml"

def generate_files():
    # Initialize cloudscraper with a specific browser profile
    # Using 'nodejs' as the interpreter is often more reliable than the default
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'firefox',
            'platform': 'windows',
            'desktop': True
        },
        interpreter='js2py' 
    )

    try:
        print(f"Attempting to bypass Cloudflare and fetch: {JSON_URL}")
        
        # Cloudscraper will automatically wait ~5 seconds for the challenge
        response = scraper.get(JSON_URL, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        
        os.makedirs(SUBDIR, exist_ok=True)
        
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
        print("Playlist and EPG generated successfully.")

    except Exception as e:
        print(f"Cloudscraper failed: {e}")
        raise

if __name__ == "__main__":
    generate_files()

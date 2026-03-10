import json
import requests
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
    # Headers exactly matching your Firefox request to bypass Cloudflare 403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": f"{BASE}/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0, i"
    }

    try:
        print(f"Fetching data from {JSON_URL}...")
        response = requests.get(JSON_URL, headers=headers, timeout=15)
        
        # Log rate limit status for monitoring
        remaining = response.headers.get('x-ratelimit-remaining')
        if remaining:
            print(f"Rate Limit Remaining: {remaining}")

        response.raise_for_status()
        data = response.json()
        
        # Ensure the directory exists so the script doesn't fail
        os.makedirs(SUBDIR, exist_ok=True)
        
        # Save a local copy of the raw events
        with open(f"{SUBDIR}/events.json", 'w') as f:
            json.dump(data, f, indent=4)

        m3u_lines = [f'#EXTM3U x-tvg-url="{XML_URL}"']
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE tv SYSTEM "xmltv.dtd">',
            '<tv generator-info-name="BuddyChewChew-Pixel-Gen">'
        ]

        for event in data.get('events', []):
            ch = event.get('channel', {})
            ch_id = ch.get('_id')
            if not ch_id: continue
                
            tv_name = ch.get('TVName', 'Unknown Channel')
            sport = event.get('sport', 'Sports')
            logo = event.get('away_logo', '')
            
            # M3U Entry with VLC headers for stream compatibility
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{sport}",{tv_name}')
            m3u_lines.append(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}')
            m3u_lines.append(f'#EXTVLCOPT:http-referrer={headers["Referer"]}')
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
        print("Update completed successfully.")

    except Exception as e:
        print(f"Error during update: {e}")
        # Re-raise error to force GitHub Action to stop if file generation fails
        raise

if __name__ == "__main__":
    generate_files()

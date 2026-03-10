import json
import requests
import os
from datetime import datetime, timedelta

# Configuration
JSON_URL = "https://pixelsport.tv/backend/liveTV/events"
USERNAME = "BuddyChewChew"
REPO = "sports"
SUBDIR = "pixel"
# This URL is what players like TiviMate will use to find your guide
XML_URL = f"https://raw.githubusercontent.com/{USERNAME}/{REPO}/main/{SUBDIR}/epg.xml"

def generate_files():
    try:
        # Fetch fresh data from the live link
        response = requests.get(JSON_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Ensure the pixel directory exists
        os.makedirs(SUBDIR, exist_ok=True)
        
        # Save a local copy of the raw JSON for your records
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
            if not ch_id:
                continue
                
            tv_name = ch.get('TVName', 'Unknown Channel')
            sport = event.get('sport', 'Sports')
            logo = event.get('away_logo', '')
            
            # 1. Build M3U Entry
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{sport}",{tv_name}')
            m3u_lines.append(f"https://pixelsport.tv/live/{ch_id}.m3u8")

            # 2. Build EPG Entry
            # Parsing date (e.g., 2026-03-10T02:00:00.000Z)
            try:
                start_dt = datetime.strptime(event.get('date'), '%Y-%m-%dT%H:%M:%S.%fZ')
                xml_start = start_dt.strftime('%Y%m%d%H%M%S +0000')
                # Programs default to 3 hours unless it's live/final
                xml_stop = (start_dt + timedelta(hours=3)).strftime('%Y%m%d%H%M%S +0000')
            except:
                continue

            xml_lines.append(f'  <channel id="{ch_id}">')
            xml_lines.append(f'    <display-name>{tv_name}</display-name>')
            xml_lines.append(f'  </channel>')
            
            xml_lines.append(f'  <programme start="{xml_start}" stop="{xml_stop}" channel="{ch_id}">')
            xml_lines.append(f'    <title lang="en">{event.get("matchName")}</title>')
            xml_lines.append(f'    <desc lang="en">Status: {event.get("gameStatusDetail")} | Location: {event.get("location")}</desc>')
            xml_lines.append(f'    <category lang="en">{sport}</category>')
            xml_lines.append(f'    <icon src="{logo}" />')
            xml_lines.append(f'  </programme>')

        xml_lines.append('</tv>')

        # Write the final files
        with open(f"{SUBDIR}/playlist.m3u8", 'w') as f:
            f.write('\n'.join(m3u_lines))
        
        with open(f"{SUBDIR}/epg.xml", 'w') as f:
            f.write('\n'.join(xml_lines))
            
        print("Update completed successfully.")

    except Exception as e:
        print(f"Error during update: {e}")

if __name__ == "__main__":
    generate_files()
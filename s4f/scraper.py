import httpx
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re

class SportsScraper:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.api_url = "https://my-dev--master-gqd4.diploi.me/api/channels"
        self.web_base = "https://my-dev--worker-1-x5wz.diploi.me/hls"
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def run(self):
        try:
            with httpx.Client(headers=self.headers, timeout=20.0) as client:
                response = client.get(self.api_url)
                data = response.json()
        except Exception as e:
            print(f"Error: {e}")
            return

        m3u_full = [f'#EXTM3U x-tvg-url="https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"']
        
        for ch in data:
            name = ch.get('name', 'Unknown').strip()
            logo = ch.get('logo', '').strip()
            
            # ID Extraction
            original_stream = ch.get('stream', '')
            extracted_id = original_stream.split('id=')[-1] if "id=" in original_stream else ch.get('tvgId')
            if not extracted_id: continue

            # TiviMate optimized URL
            stream_url = f"{self.web_base}?id={extracted_id}&type=.m3u8"
            
            # Grouping logic
            match = re.search(r'^([A-Z0-9]{2,3})\|', name)
            group = match.group(1).upper() if match else "OTHER"
            unique_tvg_id = f"s4f_{extracted_id}"

            # Format entry: No spaces after comma, added tvg-name
            entry = f'#EXTINF:-1 tvg-id="{unique_tvg_id}" tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n{stream_url}'
            m3u_full.append(entry)

        with open(os.path.join(self.output_dir, "s4f_playlist.m3u8"), "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_full))

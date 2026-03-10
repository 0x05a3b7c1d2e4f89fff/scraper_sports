import httpx
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import re

class SportsScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Referer": "https://sports4free.ru/",
            "Origin": "https://sports4free.ru/"
        }
        
        # The live API source
        self.api_url = "https://my-dev--master-gqd4.diploi.me/api/channels"
        
        # The REAL web address to replace localhost
        self.web_base = "https://my-dev--worker-1-x5wz.diploi.me/hls"
        
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def get_clean_group(self, name, raw_group):
        """Extracts |XX| tags or cleans up the PPV/Adult categories."""
        # 1. Check for country tags like |ES|, |TR|, |US| in the name
        match = re.search(r'\|([A-Z0-9]{2,3})\|', name)
        if match:
            return match.group(1).upper()
        
        # 2. Check the raw group for known categories
        raw_group = raw_group.upper()
        if "PPV" in raw_group: return "PPV"
        if "ADULT" in raw_group or "+18" in raw_group: return "ADULTS"
        
        return "OTHER"

    def run(self):
        try:
            with httpx.Client(headers=self.headers, timeout=20.0) as client:
                response = client.get(self.api_url)
                data = response.json()
        except Exception as e:
            print(f"Failed to fetch live data: {e}")
            return

        m3u_lines = [f'#EXTM3U x-tvg-url="https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"']
        cleaned_channels = []

        for ch in data:
            name = ch.get('name', 'Unknown')
            logo = ch.get('logo', '')
            raw_group = ch.get('group', 'Other')
            
            # FIX: Replace localhost with the web version
            # If the API gives "http://localhost:3000/hls?id=123", we want "https://.../hls?id=123"
            original_stream = ch.get('stream', '')
            if "localhost" in original_stream:
                channel_id = original_stream.split('id=')[-1]
                stream_url = f"{self.web_base}?id={channel_id}"
            else:
                stream_url = original_stream

            group = self.get_clean_group(name, raw_group)
            tvg_id = f"s4f_{ch.get('tvgId', channel_id)}"

            # Add to JSON list
            cleaned_channels.append({
                "name": name,
                "logo": logo,
                "group": group,
                "tvgId": tvg_id,
                "stream": stream_url
            })

            # Add to M3U8
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u_lines.append(stream_url)

        # Save the files
        with open(os.path.join(self.output_dir, "s4f_data.json"), "w", encoding="utf-8") as f:
            json.dump(cleaned_channels, f, indent=4)
            
        with open(os.path.join(self.output_dir, "s4f_playlist.m3u8"), "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))

        print(f"Processed {len(cleaned_channels)} channels to {self.output_dir}")

if __name__ == "__main__":
    SportsScraper().run()

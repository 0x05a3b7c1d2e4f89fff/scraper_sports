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
        # Pulling from the live API
        self.api_url = "https://my-dev--master-gqd4.diploi.me/api/channels"
        # Base URL for your worker
        self.web_base = "https://my-dev--worker-1-x5wz.diploi.me/hls"
        
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def get_clean_group(self, name, raw_group):
        """Extracts group tags like TR|, US|, MA| or PPV."""
        # Matches 'US|', 'TR|', 'PPV|' at the very start of the channel name
        match = re.search(r'^([A-Z0-9]{2,3})\|', name)
        if match:
            return match.group(1).upper()
        
        # Fallback to checking the raw group field from the JSON
        rg = str(raw_group).upper()
        if "PPV" in rg: return "PPV"
        if "ADULT" in rg or "+18" in rg: return "ADULTS"
        return "OTHER"

    def run(self):
        try:
            with httpx.Client(headers=self.headers, timeout=20.0) as client:
                response = client.get(self.api_url)
                data = response.json()
        except Exception as e:
            print(f"Error fetching live data: {e}")
            return

        m3u_lines = [f'#EXTM3U x-tvg-url="https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"']
        root = ET.Element("tv")

        for ch in data:
            name = ch.get('name', 'Unknown')
            logo = ch.get('logo', '')
            
            # Extract the ID correctly from the original stream URL
            original_stream = ch.get('stream', '')
            extracted_id = None
            if "id=" in original_stream:
                extracted_id = original_stream.split('id=')[-1]
            else:
                extracted_id = ch.get('tvgId')

            if not extracted_id:
                continue

            # TIVIMATE FORMAT: Append the ID and the fake extension parameter
            # Result: https://.../hls?id=1237348&type=.m3u8
            stream_url = f"{self.web_base}?id={extracted_id}&type=.m3u8"
            
            group = self.get_clean_group(name, ch.get('group', ''))
            unique_tvg_id = f"s4f_{extracted_id}"

            # Add to M3U8
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{unique_tvg_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u_lines.append(stream_url)

            # Add to EPG
            channel_node = ET.SubElement(root, "channel", id=unique_tvg_id)
            ET.SubElement(channel_node, "display-name").text = name
            prog = ET.SubElement(root, "programme", 
                                start=datetime.now().strftime("%Y%m%d%H0000 +0000"),
                                stop=datetime.now().strftime("%Y%m%d%H5900 +0000"),
                                channel=unique_tvg_id)
            ET.SubElement(prog, "title").text = f"LIVE: {name}"

        # Save M3U8 and EPG
        with open(os.path.join(self.output_dir, "s4f_playlist.m3u8"), "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
        
        tree = ET.ElementTree(root)
        tree.write(os.path.join(self.output_dir, "s4f_epg.xml"), encoding="utf-8", xml_declaration=True)
        
        print(f"Success: Processed {len(m3u_lines)//2} channels with TiviMate fix.")

if __name__ == "__main__":
    SportsScraper().run()

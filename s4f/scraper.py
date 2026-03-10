import httpx
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

class SportsScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Referer": "https://sports4free.ru/",
            "Origin": "https://sports4free.ru/",
            "Accept": "application/json, text/plain, */*"
        }
        
        self.api_channels = "https://my-dev--master-gqd4.diploi.me/api/channels"
        self.stream_template = "https://my-dev--worker-1-x5wz.diploi.me/hls?id={}"
        
        # Link to the EPG file in your repository
        self.epg_url = "https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"
        
        # Absolute path to the s4f folder
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_data(self):
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                response = client.get(self.api_channels)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error fetching: {e}")
            return None

    def run(self):
        channels = self.fetch_data()
        if not channels:
            return

        # 1. Build M3U8 with unique IDs and group-title
        m3u_content = f'#EXTM3U x-tvg-url="{self.epg_url}"\n'
        
        # XMLTV Root for EPG
        root = ET.Element("tv")

        for index, ch in enumerate(channels):
            name = ch.get('name', 'Unknown')
            base_id = ch.get('id', '1186699')
            # Create a unique ID to prevent EPG clashing
            unique_id = f"s4f_{base_id}_{index}"
            
            stream_url = self.stream_template.format(base_id)
            group = ch.get('group_name', 'Sports')
            logo = ch.get('logo', '')
            
            # M3U Entry
            m3u_content += f'#EXTINF:-1 tvg-id="{unique_id}" tvg-logo="{logo}" group-title="{group}",{name}\n{stream_url}\n'
            
            # XMLTV Entry
            channel_node = ET.SubElement(root, "channel", id=unique_id)
            ET.SubElement(channel_node, "display-name").text = name
            
            prog = ET.SubElement(root, "programme", 
                                start=datetime.now().strftime("%Y%m%d%H0000 +0000"),
                                stop=datetime.now().strftime("%Y%m%d%H5900 +0000"),
                                channel=unique_id)
            ET.SubElement(prog, "title").text = f"LIVE: {name}"

        # 2. Write Files
        with open(os.path.join(self.output_dir, "s4f_playlist.m3u8"), "w", encoding="utf-8") as f:
            f.write(m3u_content)
            
        tree = ET.ElementTree(root)
        tree.write(os.path.join(self.output_dir, "s4f_epg.xml"), encoding="utf-8", xml_declaration=True)

        print(f"Updated {len(channels)} channels in s4f/ folder.")

if __name__ == "__main__":
    scraper = SportsScraper()
    scraper.run()

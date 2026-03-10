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
            "Origin": "https://sports4free.ru/",
            "Accept": "application/json, text/plain, */*"
        }
        
        self.api_channels = "https://my-dev--master-gqd4.diploi.me/api/channels"
        self.stream_base = "https://my-dev--worker-1-x5wz.diploi.me/hls"
        self.epg_url = "https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"
        
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

    def get_group_from_name(self, name):
        """Extracts country tags like |ES|, |US|, |FR| etc. from the name."""
        match = re.search(r'\|([A-Z]{2})\|', name)
        if match:
            return match.group(1).upper()
        return "Other"

    def run(self):
        channels = self.fetch_data()
        if not channels:
            return

        m3u_content = f'#EXTM3U x-tvg-url="{self.epg_url}"\n'
        root = ET.Element("tv")

        for ch in channels:
            name = ch.get('name', 'Unknown')
            # Fix: Pull the actual ID for this channel
            channel_id = str(ch.get('id', '1186699'))
            stream_url = f"{self.stream_base}?id={channel_id}"
            
            # Determine Grouping based on name tags
            group = self.get_group_from_name(name)
            logo = ch.get('logo', '')
            unique_id = f"s4f_{channel_id}"

            # M3U8 Entry
            m3u_content += f'#EXTINF:-1 tvg-id="{unique_id}" tvg-logo="{logo}" group-title="{group}",{name}\n{stream_url}\n'

            # EPG Entry
            channel_node = ET.SubElement(root, "channel", id=unique_id)
            ET.SubElement(channel_node, "display-name").text = name
            prog = ET.SubElement(root, "programme", 
                                start=datetime.now().strftime("%Y%m%d%H0000 +0000"),
                                stop=datetime.now().strftime("%Y%m%d%H5900 +0000"),
                                channel=unique_id)
            ET.SubElement(prog, "title").text = f"LIVE: {name}"

        # Save M3U8 and EPG
        with open(os.path.join(self.output_dir, "s4f_playlist.m3u8"), "w", encoding="utf-8") as f:
            f.write(m3u_content)
            
        tree = ET.ElementTree(root)
        tree.write(os.path.join(self.output_dir, "s4f_epg.xml"), encoding="utf-8", xml_declaration=True)

        print(f"Processed {len(channels)} channels into groups: ES, US, and Other.")

if __name__ == "__main__":
    scraper = SportsScraper()
    scraper.run()

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
        
        # Embedded EPG URL for the M3U8 header
        self.epg_url = "https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"
        
        # Absolute path to ensure files are written in the s4f directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_data(self):
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                response = client.get(self.api_channels)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def generate_epg(self, channels):
        """Creates a basic XMLTV file so the M3U8 has a valid target."""
        root = ET.Element("tv")
        for ch in channels:
            ch_id = str(ch.get('id', ''))
            channel_node = ET.SubElement(root, "channel", id=ch_id)
            ET.SubElement(channel_node, "display-name").text = ch.get('name', 'Unknown')
            
            # Placeholder program
            prog = ET.SubElement(root, "programme", 
                                start=datetime.now().strftime("%Y%m%d%H0000 +0000"),
                                stop=datetime.now().strftime("%Y%m%d%H5900 +0000"),
                                channel=ch_id)
            ET.SubElement(prog, "title").text = f"LIVE: {ch.get('name')}"
            ET.SubElement(prog, "desc").text = "Live Sports Broadcast"

        tree = ET.ElementTree(root)
        epg_path = os.path.join(self.output_dir, "s4f_epg.xml")
        tree.write(epg_path, encoding="utf-8", xml_declaration=True)
        return epg_path

    def run(self):
        channels = self.fetch_data()
        if not channels:
            print("No channels found. Exiting.")
            return

        # 1. Build M3U8
        m3u_content = f'#EXTM3U x-tvg-url="{self.epg_url}"\n'
        for ch in channels:
            name = ch.get('name', 'Unknown')
            ch_id = ch.get('id', '1186699')
            stream_url = self.stream_template.format(ch_id)
            group = ch.get('group_name', 'Sports')
            logo = ch.get('logo', '')
            
            m3u_content += f'#EXTINF:-1 tvg-id="{ch_id}" tvg-logo="{logo}" group-title="{group}",{name}\n{stream_url}\n'

        # 2. Write Files (Force creation)
        m3u_path = os.path.join(self.output_dir, "s4f_playlist.m3u8")
        with open(m3u_path, "w", encoding="utf-8") as f:
            f.write(m3u_content)
            
        json_path = os.path.join(self.output_dir, "s4f_data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(channels, f, indent=4)

        epg_path = self.generate_epg(channels)

        print(f"Success! Created:\n - {m3u_path}\n - {json_path}\n - {epg_path}")

if __name__ == "__main__":
    scraper = SportsScraper()
    scraper.run()

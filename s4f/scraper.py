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
        
        self.api_url = "https://my-dev--master-gqd4.diploi.me/api/channels"
        self.web_base = "https://my-dev--worker-1-x5wz.diploi.me/hls"
        
        self.output_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(self.output_dir, exist_ok=True)

    def get_clean_group(self, name, raw_group):
        """Extracts country tags like US|, ES|, TR| or categorizes others."""
        # This regex now looks for 'US|', 'ES|', etc. at the start of the name
        match = re.search(r'^([A-Z]{2,3})\|', name)
        if match:
            return match.group(1).upper()
        
        # Fallback to checking for |US| format just in case
        match_alt = re.search(r'\|([A-Z]{2,3})\|', name)
        if match_alt:
            return match_alt.group(1).upper()
        
        raw_group = raw_group.upper()
        if "PPV" in raw_group: return "PPV"
        if "ADULT" in raw_group or "+18" in raw_group: return "ADULTS"
        
        return "Other"

    def run(self):
        try:
            with httpx.Client(headers=self.headers, timeout=20.0) as client:
                response = client.get(self.api_url)
                data = response.json()
        except Exception as e:
            print(f"Failed to fetch live data: {e}")
            return

        m3u_lines = [f'#EXTM3U x-tvg-url="https://raw.githubusercontent.com/BuddyChewChew/sports/main/s4f/s4f_epg.xml"']
        cleaned_json = []
        root = ET.Element("tv")

        for ch in data:
            name = ch.get('name', 'Unknown')
            logo = ch.get('logo', '')
            raw_group = ch.get('group', 'Other')
            
            # EXTRACT UNIQUE ID
            # First try to get it from the stream string, then tvgId
            original_stream = ch.get('stream', '')
            channel_id = None
            
            if "id=" in original_stream:
                channel_id = original_stream.split('id=')[-1]
            elif ch.get('tvgId'):
                channel_id = str(ch.get('tvgId'))
            else:
                channel_id = "1186699" # Last resort fallback

            stream_url = f"{self.web_base}?id={channel_id}"
            group = self.get_clean_group(name, raw_group)
            unique_tvg_id = f"s4f_{channel_id}"

            # 1. Update JSON Data
            cleaned_json.append({
                "name": name,
                "logo": logo,
                "group": group,
                "tvgId": unique_tvg_id,
                "stream": stream_url
            })

            # 2. Update M3U8
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{unique_tvg_id}" tvg-logo="{logo}" group-title="{group}",{name}')
            m3u_lines.append(stream_url)

            # 3. Update EPG
            channel_node = ET.SubElement(root, "channel", id=unique_tvg_id)
            ET.SubElement(channel_node, "display-name").text = name
            prog = ET.SubElement(root, "programme", 
                                start=datetime.now().strftime("%Y%m%d%H0000 +0000"),
                                stop=datetime.now().strftime("%Y%m%d%H5900 +0000"),
                                channel=unique_tvg_id)
            ET.SubElement(prog, "title").text = f"LIVE: {name}"

        # Save Files
        with open(os.path.join(self.output_dir, "s4f_data.json"), "w", encoding="utf-8") as f:
            json.dump(cleaned_json, f, indent=4)
            
        with open(os.path.join(self.output_dir, "s4f_playlist.m3u8"), "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
            
        tree = ET.ElementTree(root)
        tree.write(os.path.join(self.output_dir, "s4f_epg.xml"), encoding="utf-8", xml_declaration=True)

        print(f"Success: Processed {len(cleaned_json)} unique channels.")

if __name__ == "__main__":
    SportsScraper().run()

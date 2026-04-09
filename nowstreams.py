import requests
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def generate_files():
    source_url = "https://nowstreams.top/api_proxy.php"
    local_json_file = "streams.json"
    m3u_file = "nowstreams.m3u8"
    epg_file = "nowstreams.xml"
    
    # 1. Download the data
    print(f"Downloading data from {source_url}...")
    try:
        response = requests.get(source_url, timeout=15)
        response.raise_for_status()
        data = response.json()
        with open(local_json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error downloading: {e}")
        if os.path.exists(local_json_file):
            with open(local_json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            return

    matches = data.get("matches", [])

    # 2. Generate M3U8 and prepare EPG data
    root = ET.Element("tv")
    
    with open(m3u_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U x-tvg-url=\"nowstreams.xml\"\n")
        
        for match in matches:
            match_name = match.get("matchstr", "Unknown Match")
            league = match.get("league", "Sports")
            # Create a unique ID for the EPG mapping
            slug = match.get("slug", match_name.replace(" ", "_"))
            
            # EPG: Create Channel Element
            channel_id = slug
            chan_elem = ET.SubElement(root, "channel", id=channel_id)
            ET.SubElement(chan_elem, "display-name").text = match_name
            
            # EPG: Create Programme Element (Basic timing)
            start_ts = match.get("startTimestamp", 0) / 1000
            duration_mins = match.get("duration", 120)
            
            if start_ts > 0:
                start_dt = datetime.fromtimestamp(start_ts)
                end_dt = start_dt + timedelta(minutes=duration_mins)
                
                prog = ET.SubElement(root, "programme", 
                                    start=start_dt.strftime("%Y%m%d%H%M%S +0000"),
                                    stop=end_dt.strftime("%Y%m%d%H%M%S +0000"),
                                    channel=channel_id)
                ET.SubElement(prog, "title", lang="en").text = match_name
                ET.SubElement(prog, "desc", lang="en").text = f"League: {league}"

            # M3U8: Write entries
            channels = match.get("channels", [])
            for channel in channels:
                chan_label = channel.get("name", "Link")
                links = channel.get("links", [])
                if links:
                    f.write(f'#EXTINF:-1 tvg-id="{channel_id}" group-title="{league}",{match_name} ({chan_label})\n')
                    f.write(f"{links[0]}\n")

    # 3. Save EPG XML
    tree = ET.ElementTree(root)
    tree.write(epg_file, encoding="utf-8", xml_declaration=True)
    
    print(f"Generated {m3u_file} and {epg_file}")

if __name__ == "__main__":
    generate_files()

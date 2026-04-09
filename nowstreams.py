import requests
import json
import os

def generate_m3u():
    source_url = "https://nowstreams.top/api_proxy.php"
    local_json_file = "streams.json"
    output_file = "playlist.m3u"
    
    # 1. Download the latest data
    print(f"Downloading data from {source_url}...")
    try:
        response = requests.get(source_url, timeout=15)
        response.raise_for_status()
        
        # Save the JSON content to a local file
        with open(local_json_file, "w", encoding="utf-8") as f:
            json.dump(response.json(), f, indent=4)
        print(f"Data saved to {local_json_file}")
        
    except Exception as e:
        print(f"Could not download fresh data: {e}")
        if os.path.exists(local_json_file):
            print("Attempting to use existing local file...")
        else:
            return

    # 2. Read from the local JSON file
    try:
        with open(local_json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        matches = data.get("matches", [])
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            
            count = 0
            for match in matches:
                match_name = match.get("matchstr", "Unknown Match")
                league = match.get("league", "Sports")
                channels = match.get("channels", [])
                
                for channel in channels:
                    channel_name = channel.get("name", "Unknown Channel")
                    links = channel.get("links", [])
                    
                    if links:
                        # Taking the first available link
                        stream_link = links[0]
                        display_name = f"{match_name} ({channel_name})"
                        
                        # Writing M3U format
                        f.write(f'#EXTINF:-1 group-title="{league}",{display_name}\n')
                        f.write(f"{stream_link}\n")
                        count += 1
            
        print(f"Successfully created {output_file} with {count} entries.")

    except Exception as e:
        print(f"An error occurred while processing the file: {e}")

if __name__ == "__main__":
    generate_m3u()
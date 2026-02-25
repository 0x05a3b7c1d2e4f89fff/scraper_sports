import httpx
import json
import re
import asyncio
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

# Configuration
GITHUB_USERNAME = "BuddyChewChew"
REPO_NAME = "sports"
FOLDER_NAME = "power"  # The folder this script lives in
DEFAULT_LOGO = "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/powerstreams.png?raw=true"

# Ensure the script knows where to save files relative to itself
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def resolve_m3u8(client, embed_url):
    """Handles the double-hop and decryption logic."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://streams.center/",
    }
    try:
        res1 = await client.get(embed_url, headers=headers, follow_redirects=True)
        iframe_match = re.search(r'<iframe\s+src=["\']([^"\']+)["\']', res1.text)
        if not iframe_match: return embed_url
            
        inner_url = iframe_match.group(1)
        if inner_url.startswith('//'): inner_url = f"https:{inner_url}"
            
        headers["Referer"] = embed_url
        res2 = await client.get(inner_url, headers=headers, follow_redirects=True)
        
        input_match = re.search(r'input\s*:\s*["\']([A-Za-z0-9+/=]{50,})["\']', res2.text)
        if input_match:
            decrypt_res = await client.post(
                "https://streams.center/embed/decrypt.php",
                data={"input": input_match.group(1)},
                headers={**headers, "X-Requested-With": "XMLHttpRequest", "Referer": inner_url}
            )
            if decrypt_res.status_code == 200 and ".m3u8" in decrypt_res.text:
                return decrypt_res.text.strip()
    except Exception:
        pass
    return embed_url

async def scrape_streams():
    api_url = "https://backend.streamcenter.live/api/Parties?pageNumber=1&pageSize=500"
    # Updated path to point to the 'sports' repo and 'power' folder
    epg_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/main/{FOLDER_NAME}/epg.xml"
    
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        try:
            response = await client.get(api_url)
            all_games = response.json()
            
            scraped_items = []
            for game in all_games:
                video_url_str = game.get('videoUrl', '')
                if not video_url_str: continue
                for entry in video_url_str.split(';'):
                    url = entry.split('<')[0].strip() if '<' in entry else entry.strip()
                    lang = entry.split('<')[1].strip() if '<' in entry else "English"
                    if url.startswith('http'):
                        scraped_items.append({"id": str(game.get('id')), "name": f"{game.get('gameName')} ({lang})", "url": url})

            semaphore = asyncio.Semaphore(3)
            async def process(item):
                async with semaphore:
                    if ".php" in item['url']:
                        item['url'] = await resolve_m3u8(client, item['url'])
                return item

            results = await asyncio.gather(*(process(i) for i in scraped_items))
            valid_streams = [r for r in results if ".m3u8" in r['url']]

            # --- GENERATE EPG (XMLTV) ---
            root = ET.Element("tv")
            for item in valid_streams:
                channel = ET.SubElement(root, "channel", id=item["id"])
                ET.SubElement(channel, "display-name").text = item["name"]
                ET.SubElement(channel, "icon", src=DEFAULT_LOGO)
                
                start = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S +0000")
                stop = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=6)).strftime("%Y%m%d%H%M%S +0000")
                prog = ET.SubElement(root, "programme", start=start, stop=stop, channel=item["id"])
                ET.SubElement(prog, "title", lang="en").text = item["name"]
                ET.SubElement(prog, "icon", src=DEFAULT_LOGO)

            with open(os.path.join(BASE_DIR, "epg.xml"), "w") as f:
                f.write(minidom.parseString(ET.tostring(root)).toprettyxml(indent="  "))

            # --- GENERATE M3U8 ---
            with open(os.path.join(BASE_DIR, "power.m3u8"), "w") as f:
                f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
                for item in valid_streams:
                    f.write(f'#EXTINF:-1 tvg-id="{item["id"]}" tvg-logo="{DEFAULT_LOGO}" group-title="Live Sports",{item["name"]}\n')
                    f.write(f'#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)\n')
                    f.write(f'#EXTVLCOPT:http-referrer=https://streams.center/\n')
                    f.write(f'{item["url"]}\n')

            # --- GENERATE JSON ---
            with open(os.path.join(BASE_DIR, "streams.json"), "w") as f:
                json.dump(valid_streams, f, indent=4)

            print(f"Power: Success! Files saved in /{FOLDER_NAME}/ directory.")

        except Exception as e:
            print(f"Scraper Error: {e}")

if __name__ == "__main__":
    asyncio.run(scrape_streams())

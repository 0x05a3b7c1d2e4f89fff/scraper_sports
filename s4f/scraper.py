import httpx
import json
import os

class SportsScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Referer": "https://sports4free.ru/",
            "Origin": "https://sports4free.ru/",
            "Accept": "application/json, text/plain, */*"
        }
        
        self.api_groups = "https://my-dev--master-gqd4.diploi.me/api/groups"
        self.api_channels = "https://my-dev--master-gqd4.diploi.me/api/channels"
        self.stream_template = "https://my-dev--worker-1-x5wz.diploi.me/hls?id={}"
        # Ensure files are saved in the correct sub-directory
        self.output_dir = os.path.dirname(os.path.abspath(__file__))

    def fetch_endpoint(self, url):
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None

    def run(self):
        groups = self.fetch_endpoint(self.api_groups)
        channels = self.fetch_endpoint(self.api_channels)
        
        # Build a simple M3U playlist based on the data
        m3u_content = "#EXTM3U\n"
        if channels:
            for ch in channels:
                name = ch.get('name', 'Unknown')
                ch_id = ch.get('id', '1186699')
                stream_url = self.stream_template.format(ch_id)
                group = ch.get('group_name', 'Sports')
                
                m3u_content += f'#EXTINF:-1 group-title="{group}",{name}\n{stream_url}\n'

        # Save files to the s4f directory
        with open(os.path.join(self.output_dir, "s4f_data.json"), "w") as f:
            json.dump({"groups": groups, "channels": channels}, f, indent=4)
            
        with open(os.path.join(self.output_dir, "s4f_playlist.m3u"), "w") as f:
            f.write(m3u_content)

        print("Scrape complete. Files updated in s4f/")

if __name__ == "__main__":
    scraper = SportsScraper()
    scraper.run()

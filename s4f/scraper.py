import httpx
import json
import os

class SportsScraper:
    def __init__(self):
        # Mandatory headers for sports4free.ru validation
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Referer": "https://sports4free.ru/",
            "Origin": "https://sports4free.ru/",
            "Accept": "application/json, text/plain, */*"
        }
        
        # API Endpoints
        self.api_groups = "https://my-dev--master-gqd4.diploi.me/api/groups"
        self.api_channels = "https://my-dev--master-gqd4.diploi.me/api/channels"
        self.stream_template = "https://my-dev--worker-1-x5wz.diploi.me/hls?id={}"

    def fetch_endpoint(self, url):
        """Executes GET request with the required site headers."""
        try:
            with httpx.Client(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error accessing {url}: {e}")
            return None

    def get_stream_url(self, stream_id="1186699"):
        """Returns the formatted HLS link."""
        return self.stream_template.format(stream_id)

    def save_results(self, data, filename="output.json"):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Data successfully saved to {filename}")

    def run(self):
        print("Starting scrape for BuddyChewChew/sports/s4f...")
        
        results = {
            "groups": self.fetch_endpoint(self.api_groups),
            "channels": self.fetch_endpoint(self.api_channels),
            "active_stream": self.get_stream_url()
        }
        
        self.save_results(results)

if __name__ == "__main__":
    scraper = SportsScraper()
    scraper.run()
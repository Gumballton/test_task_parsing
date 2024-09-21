import argparse
import random
import scrapy
import json
import time

class ProxySpider(scrapy.Spider):
    name = "proxy_spider"

    def __init__(self, user_id, *args, **kwargs):
        """Initialize the spider with the user ID and other parameters."""
        super().__init__(*args, **kwargs)
        self.user_id = user_id
        self.proxies = []
        self.current_page = 1
        self.total_pages = 5
        self.start_time = time.time()
        self.index = 0
        self.results = {}
        self.base_delay = 15  # Base delay between requests

    def start_requests(self):
        """Start the requests to get the initial token."""
        yield scrapy.Request(
            url='https://test-rg8.ddns.net/api/get_token',
            callback=self.parse_token,
            cookies={'form_token': '6afb92fa-9475-43b5-8241-338348a62f92'}
        )

    def parse_token(self, response):
        """Parse the token from the response headers."""
        form_token = response.headers.getlist('Set-Cookie')
        token_value = None

        for cookie in form_token:
            if b'form_token=' in cookie:
                token_value = cookie.split(b'=')[1].split(b';')[0].decode('utf-8')
                self.logger.info(f'Received form_token: {token_value}')
                break

        if token_value is None:
            self.logger.error('form_token not found in response headers')
            return

        self.logger.info("Starting proxy collection.")
        return self.fetch_proxies(token_value)

    def fetch_proxies(self, form_token):
        """Fetch proxies from the proxy list pages."""
        if self.current_page <= self.total_pages:
            next_page = f'https://www.freeproxy.world/?type=&anonymity=&country=&speed=&port=&page={self.current_page}'
            self.logger.info("Requesting proxy page: %s", next_page)
            return scrapy.Request(url=next_page, callback=self.extract_proxies, meta={'form_token': form_token})
        else:
            self.logger.info("Proxy collection completed. Sending proxies...")
            return self.send_proxies()

    def extract_proxies(self, response):
        """Extract proxies from the response."""
        self.logger.info("Calling extract_proxies.")
        rows = response.css('table.layui-table tbody tr')

        for row in rows:
            ip = row.css('td.show-ip-div::text').get()
            port = row.css('td a::text').get()

            if ip and port:
                proxy = f"{ip.strip()}:{port.strip()}"
                self.proxies.append(proxy)
                self.logger.info(f"Added proxy: {proxy}")

        self.logger.info("Collected proxies: %s", self.proxies)
        self.current_page += 1
        return self.fetch_proxies(response.meta['form_token'])

    def send_proxies(self):
        """Send the collected proxies to the server."""
        if self.index < len(self.proxies):
            return scrapy.Request(
                url='https://test-rg8.ddns.net/api/get_token',
                callback=self.get_new_token,
                meta={'proxy_group': self.proxies[self.index:self.index + 10]},
                dont_filter=True
            )
        else:
            self.logger.info("All proxies sent.")
            self.save_results()
            return None

    def get_new_token(self, response):
        """Get a new token and send a group of proxies."""
        form_token = response.headers.getlist('Set-Cookie')
        token_value = None

        for cookie in form_token:
            if b'form_token=' in cookie:
                token_value = cookie.split(b'=')[1].split(b';')[0].decode('utf-8')
                self.logger.info(f'Received new form_token: {token_value}')
                break

        if token_value is None:
            self.logger.error('form_token not found in response headers')
            return

        group = response.meta['proxy_group']
        json_data = {
            "user_id": self.user_id,
            "len": len(group),
            "proxies": ", ".join(group)
        }
        self.logger.info("Data being sent: %s", json.dumps(json_data, indent=4))

        headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': f'form_token={token_value}'
        }

        delay = self.base_delay + random.uniform(0, 10)
        time.sleep(delay)

        return scrapy.Request(
            url='https://test-rg8.ddns.net/api/post_proxies',
            method='POST',
            headers=headers,
            body=json.dumps(json_data),
            callback=self.parse_response,
            meta={'group': group, 'retry_count': 0}
        )

    def parse_response(self, response):
        """Parse the response from the POST request."""
        self.logger.info('Response from POST request: %s', response.text)
        retry_count = response.meta.get('retry_count', 0)

        if response.status == 200:
            save_id = response.json().get('save_id')
            self.logger.info('Received save_id: %s', save_id)
            self.results[f"{save_id}_{self.index // 10 + 1}"] = response.meta['group']
            self.index += 10
            self.save_results() 
            return self.send_proxies()
        elif response.status == 429:
            self.logger.error(f'Rate limit hit (429). Retrying in 20 seconds...')
            time.sleep(20)
            return self.get_new_token(response)
        else:
            self.logger.error(f'Failed to send proxies: {response.status} - {response.text}')
            if retry_count < 3:
                self.logger.info("Retrying in 5 seconds...")
                time.sleep(5)
                retry_count += 1
                return self.send_proxies()
            else:
                self.index += 10
                return self.send_proxies()
    
    def save_results(self):
        """Save the collected results to a JSON file."""
        with open('results.json', 'w') as f:
            json.dump(self.results, f, indent=4)
        self.logger.info("Results saved to results.json")

    def close(self, reason):
        """Handle closing the spider and log the execution time."""
        execution_time = time.time() - self.start_time
        hours, remainder = divmod(execution_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        formatted_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
        self.logger.info("Execution time: %s", formatted_time)

        # Save execution time to time.txt
        with open('time.txt', 'w') as time_file:
            time_file.write(f"{formatted_time}\n")

# To launch the spider with command line arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--user_id", required=True, help="User ID for sending")
    args = parser.parse_args()

    process = scrapy.crawler.CrawlerProcess()
    process.crawl(ProxySpider, user_id=args.user_id)
    process.start()

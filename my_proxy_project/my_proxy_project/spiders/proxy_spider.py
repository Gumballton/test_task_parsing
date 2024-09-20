import argparse
import scrapy
import json
import time

class ProxySpider(scrapy.Spider):
    """
    Spider for collecting proxies from freeproxy.world and sending them to a specified server.

    Attributes:
        user_id (str): User ID for sending proxies.
        proxies (list): List of collected proxies.
        current_page (int): Current page of proxies.
        total_pages (int): Total number of pages to scrape.
        start_time (float): Start time of the spider execution.
    """
    name = "proxy_spider"

    def __init__(self, user_id, *args, **kwargs):
        """
        Initialize the spider.

        Args:
            user_id (str): User ID for sending proxies.
        """
        super().__init__(*args, **kwargs)
        self.user_id = user_id
        self.proxies = []
        self.current_page = 1
        self.total_pages = 5
        self.start_time = time.time()

    def start_requests(self):
        """
        Starts the request to get the token.
        """
        yield scrapy.Request(
            url='https://test-rg8.ddns.net/api/get_token',
            callback=self.parse_token,
            cookies={'form_token': '6afb92fa-9475-43b5-8241-338348a62f92'}
        )

    def parse_token(self, response):
        """
        Processes the response from the token request.

        Args:
            response (scrapy.http.Response): The server response.
        """
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
        """
        Requests the proxy page.

        Args:
            form_token (str): The form token for the request.
        """
        if self.current_page <= self.total_pages:
            next_page = f'https://www.freeproxy.world/?type=&anonymity=&country=&speed=&port=&page={self.current_page}'
            self.logger.info("Requesting proxy page: %s", next_page)
            return scrapy.Request(url=next_page, callback=self.extract_proxies, meta={'form_token': form_token})
        else:
            self.logger.info("Proxy collection completed. Sending proxies...")
            return self.post_proxies(form_token)

    def extract_proxies(self, response):
        """
        Extracts proxies from the page.

        Args:
            response (scrapy.http.Response): The server response with proxies.
        """
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

    def post_proxies(self, form_token):
        """
        Sends the collected proxies to the server.

        Args:
            form_token (str): The form token for the request.
        """
        if not self.proxies:
            self.logger.error("No collected proxies to send.")
            return

        json_data = {
            "user_id": self.user_id,
            "len": len(self.proxies[:10]),
            "proxies": ", ".join(self.proxies[:10])
        }

        self.logger.info("Data being sent: %s", json.dumps(json_data, indent=4))

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'Origin': 'https://test-rg8.ddns.net',
            'Referer': 'https://test-rg8.ddns.net/task',
            'Connection': 'keep-alive',
            'Cookie': f'form_token={form_token}',
            'X-Requested-With': 'XMLHttpRequest'
        }

        return scrapy.Request(
            url='https://test-rg8.ddns.net/api/post_proxies',
            method='POST',
            headers=headers,
            body=json.dumps(json_data),
            callback=self.parse_response
        )

    def parse_response(self, response):
        """
        Processes the response from the POST request.

        Args:
            response (scrapy.http.Response): The server response.
        """
        self.logger.info('Response from POST request: %s', response.text)
        if response.status == 200:
            self.logger.info('Proxies successfully sent.')
            self.save_proxies()
        else:
            self.logger.error(f'Failed to send proxies: {response.status} - {response.text}')

    def save_proxies(self):
        """
        Saves the collected proxies to a JSON file.
        """
        try:
            results = {}
            # Load existing data if the file already exists
            try:
                with open('results.json', 'r') as f:
                    results = json.load(f)
            except FileNotFoundError:
                pass

            # Create groups of proxies, each containing up to 50 proxies
            num_proxies = len(self.proxies)
            groups = [self.proxies[i:i + 50] for i in range(0, num_proxies, 50)]

            # Save each group under a new save_id
            for idx, group in enumerate(groups):
                save_id = f"save_id_{idx + 1}"
                results[save_id] = group

            # Save to the JSON file
            with open('results.json', 'w') as f:
                json.dump(results, f, indent=4)
            self.logger.info(f'Proxies saved to results.json with IDs: {list(results.keys())}')
        except Exception as e:
            self.logger.error(f'Error saving proxies: {e}')

    def close(self):
        """
        Called when the spider is closed.
        """
        execution_time = time.time() - self.start_time
        formatted_time = time.strftime('%H:%M:%S', time.gmtime(execution_time))
        with open('time.txt', 'w') as f:
            f.write(formatted_time)
        self.logger.info("Execution time: %s", formatted_time)

# To launch the spider with command line arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--user_id", required=True, help="User ID for sending")
    args = parser.parse_args()

    process = scrapy.crawler.CrawlerProcess()
    process.crawl(ProxySpider, user_id=args.user_id)
    process.start()

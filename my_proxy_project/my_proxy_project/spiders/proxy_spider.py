import random
import scrapy
import json
import base64
import time
from typing import List, Dict

class ProxySpider(scrapy.Spider):
    name = "proxy_spider"
    start_urls = [f'http://free-proxy.cz/en/proxylist/main/{i}' for i in range(1, 6)]

    def __init__(self, *args, **kwargs) -> None:
        """
        Initializes the ProxySpider.
        """
        super(ProxySpider, self).__init__(*args, **kwargs)
        self.proxies_dict: Dict[str, List[str]] = {}  # Dictionary to store proxies by save_id
        self.start_time: float = time.time()  # Record the start time

    def parse(self, response: scrapy.http.Response) -> None:
        """
        Parses the response from the proxy listing pages.

        :param response: The response object containing the page data.
        """
        page_number = response.url.split('/')[-1]
        rows = response.css('table#proxy_list tr')
        proxies = set()

        # Extract and decode IP addresses from the response
        for row in rows[1:]:
            ip_script = row.css('td.left script::text').get()
            if ip_script:
                encoded_ip = ip_script.split('"')[1]
                ip = base64.b64decode(encoded_ip).decode('utf-8')
                proxies.add(ip)

        # Generate a unique save_id
        current_time = time.strftime('%H:%M:%S', time.gmtime())
        save_id = f"save_id_{current_time}_{page_number}"
        self.proxies_dict[save_id] = list(proxies)

        # Add a delay before the next request
        time.sleep(random.uniform(1, 3))  # Delay between 1 to 3 seconds

    def close(self, reason: str) -> None:
        """
        Executes cleanup tasks after the spider finishes.

        :param reason: The reason for the spider closing.
        """
        # Save the collected data to results.json
        with open('results.json', 'w') as f:
            json.dump(self.proxies_dict, f, indent=4)

        # Save the execution time to time.txt
        execution_time = time.time() - self.start_time
        formatted_time = time.strftime('%H:%M:%S', time.gmtime(execution_time))
        with open('time.txt', 'w') as f:
            f.write(formatted_time)

    def start_requests(self) -> scrapy.Request:
        """
        Initiates the requests to the start URLs.

        :return: Yields requests for the start URLs.
        """
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

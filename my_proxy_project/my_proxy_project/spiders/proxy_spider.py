import random
import scrapy
import json
import base64
import time
from typing import List, Dict

class CombinedProxySpider(scrapy.Spider):
    name = "proxy_spider"
    
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proxies_dict: Dict[str, List[str]] = {}
        self.start_time = time.time()
        self.token = None
        self.user_id = kwargs.get('user_id', None)
        self.total_pages = 5
        self.current_page = 1
        self.response_received = False  # Состояние для отслеживания завершения

    def start_requests(self):
        self.logger.info("Запуск start_requests.")
        yield scrapy.Request(
            url='https://test-rg8.ddns.net/api/get_token',
            callback=self.parse_token,
            cookies={'form_token': '42de84ac-3530-411d-b302-e0453211b110'}
        )

    def parse_token(self, response):
        self.logger.info("Вызван parse_token.")
        form_token = response.headers.getlist('Set-Cookie')
        for cookie in form_token:
            if b'form_token=' in cookie:
                self.token = cookie.split(b'=')[1].split(b';')[0].decode('utf-8')
                self.logger.info(f'Получен form_token: {self.token}')
                break

        if self.token is None:
            self.logger.error('form_token не найден в заголовках ответа')
            return

        self.logger.info("Запуск сбора прокси.")
        yield from self.fetch_proxies()

    def fetch_proxies(self):
        if self.current_page <= self.total_pages:
            next_page = f'http://free-proxy.cz/en/proxylist/main/{self.current_page}'
            self.logger.info("Запрос на страницу прокси: %s", next_page)
            yield scrapy.Request(url=next_page, callback=self.extract_proxies,
                                 headers={'Referer': 'http://free-proxy.cz/en/'})

    def extract_proxies(self, response: scrapy.http.Response) -> None:
        self.logger.info("Вызван extract_proxies.")
        rows = response.css('table#proxy_list tr')
        proxies = set()

        for row in rows[1:]:
            ip_script = row.css('td.left script::text').get()
            if ip_script:
                encoded_ip = ip_script.split('"')[1]
                ip = base64.b64decode(encoded_ip).decode('utf-8')
                port = row.css('td span.fport::text').get()
                if port:
                    proxy = f"{ip}:{port}"
                    proxies.add(proxy)
                    self.logger.info(f"Добавлен прокси: {proxy}")

        current_time = time.strftime('%H:%M:%S', time.gmtime())
        save_id = f"save_id_{current_time}_{self.current_page}"
        self.proxies_dict[save_id] = list(proxies)

        self.logger.info("Собрано прокси: %s", proxies)

        self.current_page += 1

        yield from self.fetch_proxies()

        if self.current_page > self.total_pages:
            self.logger.info("Все страницы обработаны, отправка собранных прокси.")
            yield from self.send_all_proxies()

    def send_all_proxies(self):
        self.logger.info("Отправка всех собранных прокси.")
        all_proxies = [proxy for proxies in self.proxies_dict.values() for proxy in proxies]
        if all_proxies:
            proxies_string = ", ".join(all_proxies)  # Форматируем как строку
            json_data = {
                "user_id": self.user_id,
                "len": len(all_proxies),
                "proxies": proxies_string  # Используем строку прокси
            }

            self.logger.debug(f"Отправляемые данные: {json_data}")

            yield scrapy.http.JsonRequest(
                url='https://test-rg8.ddns.net/api/post_proxies',
                data=json.dumps(json_data),
                callback=self.parse_response,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.token}',  # Используйте ваш токен
                }
            )

    def parse_response(self, response):
        self.logger.info('Response от POST запроса: %s', response.text)
        if response.status == 200:
            self.logger.info('Форма успешно отправлена.')
        else:
            self.logger.error(f'Не удалось отправить форму: {response.text}')

        # Устанавливаем флаг, что ответ получен
        self.response_received = True

        # Закрываем паука, если это последний ответ
        if self.current_page > self.total_pages:
            self.close(reason='finished')

    def close(self, reason: str) -> None:
        self.logger.info("Закрытие паука с причиной: %s", reason)
        with open('results.json', 'w') as f:
            json.dump(self.proxies_dict, f, indent=4)

        execution_time = time.time() - self.start_time
        formatted_time = time.strftime('%H:%M:%S', time.gmtime(execution_time))
        with open('time.txt', 'w') as f:
            f.write(formatted_time)
        self.logger.info("Время выполнения: %s", formatted_time)

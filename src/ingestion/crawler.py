from abc import ABC, abstractmethod
import base64
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
import random
import asyncio 

class CrawlerMachine(ABC):
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session: AsyncSession | None = None 

    async def __aenter__(self):
        self.session = AsyncSession(impersonate="chrome")  
        return self 
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _fetch_html(self, url: str, max_retries: int = 5) -> str:
        # Lặp thử tối đa max_retries lần (attempt chạy từ 1 đến 5)
        for attempt in range(1, max_retries + 1):
            # Giãn cách cơ bản giữa các request để hạn chế chạm ngưỡng 429
            delay = 1.5 + random.random() * 1.5
            await asyncio.sleep(delay)

            try:
                if self.session is not None:
                    response = await self.session.get(url, timeout=self.timeout)
                else:
                    async with AsyncSession(impersonate="chrome") as temp_session:
                        response = await temp_session.get(url, timeout=self.timeout)

                # Trường hợp 1: Thành công (HTTP 200) -> trả kết quả ngay, thoát vòng lặp!
                if response.status_code == 200:
                    return response.text

                # Trường hợp 2: Bị phạt quá tốc độ (HTTP 429) hoặc server quá tải tạm thời (500, 502, 503, 504)
                if response.status_code in (429, 500, 502, 503, 504):
                    # Kiểm tra xem server có dặn cần chờ bao nhiêu giây trong header 'Retry-After' không
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait_time = int(retry_after) + 1.0
                    else:
                        # Exponential Backoff: Lần 1 chờ ~6s, lần 2 chờ ~12s, lần 3 chờ ~24s...
                        wait_time = (5.0 * (2 ** (attempt - 1))) + random.random() * 2.0

                    # Nếu chưa hết số lần thử thì ngủ chờ hết giờ phạt rồi vòng lên thử lại
                    if attempt < max_retries:
                        await asyncio.sleep(wait_time)
                        continue

                # Nếu là lỗi khác (như 404 Không tìm thấy trang) thì báo lỗi luôn, không cần thử lại
                raise ValueError(f"Error loading page, HTTP: {response.status_code}")

            except Exception as e:
                # Nếu bị rớt mạng / timeout ở lần thử cuối cùng thì mới chịu thua
                if attempt == max_retries:
                    raise e
                # Còn lượt thử thì chờ một chút rồi thử lại
                await asyncio.sleep(3.0 * attempt)

    @abstractmethod
    def parse_chapter_list(self, raw_html: str, novel_url: str) -> list[str]:
        pass

    async def get_chapter_list(self, novel_url: str) -> list[str]:
        raw_html = await self._fetch_html(novel_url)
        return self.parse_chapter_list(raw_html, novel_url)

    @abstractmethod
    def parse_chapter(self, raw_html: str) -> tuple[str, str]:
        pass 

    async def get_chapter_data(self, url: str) -> tuple[str, str]:
        raw_html = await self._fetch_html(url)
        return self.parse_chapter(raw_html)


class DocLnCrawler(CrawlerMachine):
    @staticmethod
    def _extracted_protected_data(soup: BeautifulSoup) -> tuple[str, str, list[str]]:
        protected_data = soup.find("div", id="chapter-c-protected")
        if not protected_data:
            raise ValueError("Không tìm thấy thẻ chapter-c-protected")
        scheme = protected_data.get("data-s")
        key = protected_data.get("data-k")
        raw_chunks = protected_data.get("data-c")
        chunk_list = json.loads(raw_chunks)
        return scheme, key, chunk_list 
    
    @staticmethod
    def _unshuffle_chunk(chunk_list: list[str]) -> list[str]:
        chunk_list.sort(key=lambda chunk: int(chunk[:4]))
        clean_b64_chunks = []
        for chunk in chunk_list:
            b64_chunk = chunk[4:]
            clean_b64_chunks.append(b64_chunk)
        return clean_b64_chunks

    @staticmethod
    def _decode_xor_chunk(key: str, b64_chunk: str) -> bytes:
        key_bytes = key.encode("utf-8")
        key_len = len(key_bytes)
        chunk_byte = base64.b64decode(b64_chunk)
        decode_bytes = bytearray()
        for i, byte in enumerate(chunk_byte):
            encode_byte = byte ^ key_bytes[i % key_len]
            decode_bytes.append(encode_byte)
        return bytes(decode_bytes)

    def parse_chapter_list(self, raw_html: str, novel_url: str) -> list[str]:
        soup = BeautifulSoup(raw_html, "lxml")
        chapter_tags = soup.select("ul.list-chapters a[href]")
        if not chapter_tags:
            chapter_tags = soup.select("div.chapter-name a[href]")

        chapter_urls: list[str] = []
        seen: set[str] = set()

        for a_tag in chapter_tags:
            href = a_tag.get("href", "").strip()
            if not href:
                continue
            full_url = urljoin(novel_url, href)
            if full_url not in seen:
                seen.add(full_url)
                chapter_urls.append(full_url)

        return chapter_urls

    def parse_chapter(self, raw_html: str) -> tuple[str, str]:
        soup = BeautifulSoup(raw_html, "lxml")
        title_tag = soup.find("h4", class_="title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        _, key, chunk_list = self._extracted_protected_data(soup)
        clean_b64_chunks = self._unshuffle_chunk(chunk_list)
        chapter_content_list = []
        for chunk in clean_b64_chunks:
            content = self._decode_xor_chunk(key, chunk)
            chapter_content_list.append(content)
        full_chapter_html = b"".join(chapter_content_list).decode("utf-8")
        return title_text, full_chapter_html

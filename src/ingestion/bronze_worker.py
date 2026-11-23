import asyncio
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from src.ingestion.crawler import CrawlerMachine 


class BronzeWorker:
    def __init__(self, crawler: CrawlerMachine, output_dir: str, max_concurrent: int, logger: logging.Logger):
        self.crawler = crawler
        self.logger = logger 
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok= True)

    def _get_filepath(self,index: int, url: str) -> Path:
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]   
        return self.output_dir/f"chap_{index:04d}_{url_hash}.json"

    async def _process_single_url(self, index: int, url: str) -> bool:
        file_path = self._get_filepath(index, url)
        
        if file_path.exists():
            self.logger.debug("File Exist: %s", file_path)
            return True
        async with self.semaphore:
            try:
                title, raw_content_html = await self.crawler.get_chapter_data(url)
                payload = {
                    "metadata": {
                        "chapter_index": index,
                        "title": title,
                        "url": url,
                        "crawled_at": datetime.now(timezone.utc).isoformat()
                    },
                    "raw_content_html": raw_content_html
                }
                with open(file_path, mode="w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                self.logger.info("File saved successfully, path:%s", file_path)

            except Exception as e:
                self.logger.error(f"Error in chapter: {index} ({url}): {e}", exc_info = True)
                return False 
            return True 

    async def run_batch(self, urls: list[str]):
        self.logger.info(f"Start the work at Bronze layer {len(urls)} URL.")
        
        async with self.crawler:
            tasks = [
                self._process_single_url(index, url)
                for index, url in enumerate(urls, start=1)
            ]
            results = await asyncio.gather(*tasks)

        successful_count = sum(results)
        self.logger.info(
            "Finished work in Bronze layer: %d/%d chapters downloaded successfully.",
            successful_count,
            len(urls),
        )

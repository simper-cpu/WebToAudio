import asyncio 
from src.utils.logger_setup import get_logger
from src.ingestion.crawler import DocLnCrawler
from src.ingestion.bronze_worker import BronzeWorker

async def main():
    novel_url = "https://docln.net/truyen/7015-breakthrough-with-the-forbidden-master"
    pipeline_logger = get_logger(name="BronzePipeline", log_file="log/Pipeline_log.log")
    docln_crawler = DocLnCrawler(timeout=10)
    output_folder = "data/bronze/docln/break-through-with-the-forbidden-master"
    max_concurrent_tasks = 3

    pipeline_logger.info(f"Getting chapter list from: {novel_url}")
    all_urls = await docln_crawler.get_chapter_list(novel_url)
    pipeline_logger.info(f"Found {len(all_urls)} chapters.")

    urls_to_crawl = all_urls

    worker = BronzeWorker(
        crawler=docln_crawler,
        output_dir=output_folder,
        max_concurrent=max_concurrent_tasks,
        logger=pipeline_logger
    ) 
    await worker.run_batch(urls_to_crawl)

if __name__ == "__main__":
    asyncio.run(main())

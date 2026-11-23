# Tiến độ Dự án: Novel-to-Audio Data Pipeline

## 1. Kiến trúc Tổng thể & Công nghệ
- **Mô hình kiến trúc:** Medallion Architecture (Bronze -> Silver -> Gold) kết hợp OOP (Abstract Base Class, Dependency Injection).
- **Tech Stack hiện tại:** Python, `asyncio` (Semaphore, gather), `curl_cffi` (AsyncSession impersonate chrome), `BeautifulSoup4` (`lxml`), `hashlib` (MD5), `logging`.
- **Cấu trúc thư mục hiện hành:**
  - `main.py`: Entry point điều phối toàn bộ pipeline.
  - `src/utils/logger_setup.py`: Cấu hình `get_logger` (StreamHandler & FileHandler).
  - `src/ingestion/crawler.py`: Chứa `CrawlerMachine` (Base ABC) và `DocLnCrawler` (xử lý bóc tách mục lục, sắp xếp chunk Base64 và giải mã XOR).
  - `src/ingestion/bronze_worker.py`: Chứa `BronzeWorker` quản lý luồng tải bất đồng bộ, kiểm tra idempotency qua tên file băm MD5 và lưu trữ JSON tầng Bronze.

## 2. Trạng thái các Giai đoạn (Milestones)

### Phase 1 & 2: Ingestion & Tầng Bronze [ĐANG HOÀN THIỆN - 90%]
- [x] Thiết kế `logger_setup.py` tách biệt log màn hình và file `log/Pipeline_log.log`.
- [x] Xây dựng `CrawlerMachine` quản lý phiên mạng và `DocLnCrawler` giải mã XOR dữ liệu từ `docln`.
- [x] Xây dựng `BronzeWorker` kiểm tra trùng lặp bằng mã băm MD5, đóng gói `metadata` (`chapter_index`, `title`, `url`, `crawled_at`) cùng `raw_content_html` xuống `data/bronze/`.
- [ ] **Vấn đề đang xử lý (Active Issue):** Khắc phục lỗi `HTTP 429 Too Many Requests` khi cào số lượng lớn chương truyện bằng cách bổ sung `asyncio.sleep` có độ trễ ngẫu nhiên (jitter) trong `_fetch_html` và tinh chỉnh `max_concurrent_tasks`.
- [ ] Chuẩn hóa tên file lưu trữ theo định dạng kết hợp `chap_{index:04d}_{url_hash}.json`.

### Phase 3: Tầng Silver - Data Cleaning & Text Normalization [CHƯA BẮT ĐẦU - 0%]
- [ ] Thiết kế class `TextCleaner`: Bóc tách văn bản từ `raw_content_html`, loại bỏ thẻ rác bằng `.decompose()`, chuẩn hóa Unicode tiếng Việt (`NFC`) và lọc ký tự nhiễu bằng Regex (`re`).
- [ ] Chia nhỏ văn bản thành các đoạn ngắn (`tts_chunks`) vừa với giới hạn ngữ cảnh của mô hình đọc âm thanh.
- [ ] Thiết kế `SilverWorker` đọc từ `data/bronze/`, xử lý đồng bộ và lưu kết quả sang `data/silver/`.

### Phase 4: Tầng Gold - Audio Generation & Packaging [CHƯA BẮT ĐẦU - 0%]
- [ ] Tích hợp engine Text-to-Speech tạo file âm thanh MP3/EPUB từ `tts_chunks`.
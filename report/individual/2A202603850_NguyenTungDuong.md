# Báo cáo Day 7 — Agentic RAG

**Họ và tên:** Nguyễn Tùng Dương  
**Mã sinh viên:** 2A202603850  
**Lớp:** K5-L3B  
**Repository:** `K5-L3B-DAY07-2A202603850-NguyenTungDuong-RetrievalContext`

---

## 1. Dữ liệu và benchmark

- **Nguồn tài liệu, quyền sử dụng, số trang và số chunk:**
  - Tài liệu: Tóm tắt luận án Tiến sĩ Xã hội học *"Ảnh hưởng của việc sử dụng mạng xã hội Facebook đến học tập và đời sống của sinh viên hiện nay"* (NCS Nguyễn Lan Nguyên, ĐHQGHN, 2020).
  - Quyền sử dụng: Sử dụng cho mục đích học tập và nghiên cứu trong khuôn khổ khóa học VinUni-AI20k.
  - Quy mô: 28 trang nội dung học thuật tiếng Việt, chia thành **71 chunks** (chiến lược `strategy_b` — chia theo đoạn văn bản tự nhiên kết hợp ràng buộc độ dài tối đa 800 ký tự từ Day 6).
- **Vector store, embedding model, phiên bản và số chiều:**
  - Vector Store: **PostgreSQL 16 + pgvector 0.8.7** (chạy trên Docker container local tại cổng 55433).
  - Embedding Model: **Gemini Embedding** (`gemini-embedding-001`, endpoint Google Generative Language v1beta).
  - Cấu hình vector: **768 chiều** (`outputDimensionality: 768`, chuẩn hóa taskType `RETRIEVAL_DOCUMENT` và `RETRIEVAL_QUERY`).
- **Agent model, cách chạy và phân chia dev/test:**
  - Agent Controller: **Gemini Flash Lite** (`gemini-flash-lite-latest`), cấu hình `temperature=0.1` với `responseMimeType="application/json"` đảm bảo cấu trúc hành động (`search` hoặc `answer`).
  - Cách chạy: Vòng lặp Agentic RAG tự động điều phối trong `starter/agentic.py` (tối đa `max_searches=3`, `top_k=3`, `budget=2500` ký tự context).
  - Phân chia Benchmark: Tổng cộng **24 câu hỏi** chuẩn chỉnh:
    - **Tập Dev (17 câu):** 15 câu có đáp án trong tài liệu + 2 câu thiếu bằng chứng (`absence_reason`).
    - **Tập Test (7 câu):** 5 câu có đáp án trong tài liệu + 2 câu thiếu bằng chứng (`absence_reason`).
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - Câu có đáp án: Bắt buộc có trích dẫn `gold` gồm `source_id`, `page` và đoạn văn bằng chứng nguyên văn `evidence` nằm trọn vẹn trong một chunk.
  - Câu thiếu bằng chứng: Các câu hỏi gần với chủ đề nhưng nội dung hoàn toàn không xuất hiện trong tài liệu (ví dụ: số liệu thời lượng dùng TikTok, mức học phí nhà trường, ngân sách tài trợ bằng tiền, thuật toán AI nội bộ của Facebook). Yêu cầu agent phải nhận biết và chủ động từ chối (`search_and_abstain`), không được đoán mò.

---

## 2. Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|:---:|:---:|:---:|:---:|
| **Baseline** | TF-IDF Lexical, top-k=3, budget=800 | Mặc định đề bài | dev | 7/15 (46.7%) | 10/15 (66.7%) | 0/15 (0.0%) | 0.10 ms / $0 |
| **Cải thiện 1** | TF-IDF Lexical, top-k=3, budget=2500 | Tăng budget tránh cắt cụt chunk dài | dev | 7/15 (46.7%) | 10/15 (66.7%) | 9/15 (60.0%) | 0.11 ms / $0 |
| **Phương pháp 2** | Dense Retrieval (pgvector + gemini-embedding-001), top-k=3, budget=2500 | Dùng vector ngữ nghĩa thay thế từ khóa | dev | 9/15 (60.0%) | 12/15 (80.0%) | 12/15 (80.0%) | 675.7 ms / ~$0.0001 |
| **Phương pháp 3 (Chốt)** | **Hybrid Retrieval (Dense + TF-IDF với RRF k=60)**, top-k=3, budget=2500 | Hợp nhất ưu điểm ngữ nghĩa và từ khóa | dev | **9/15 (60.0%)** | **14/15 (93.3%)** | **14/15 (93.3%)** | 674.6 ms / ~$0.0001 |
| **Baseline** | TF-IDF Lexical, top-k=3, budget=800 | Đối chứng trên test | test | 4/5 (80.0%) | 4/5 (80.0%) | 0/5 (0.0%) | 0.10 ms / $0 |
| **Cấu hình đã chọn** | **Hybrid Retrieval (RRF k=60)**, top-k=3, budget=2500 | Đánh giá cấu hình chốt trên test | test | **4/5 (80.0%)** | **4/5 (80.0%)** | **4/5 (80.0%)** | 644.0 ms / ~$0.0001 |

### Phân tích lỗi trên tập Dev và lý do chọn cấu hình:

1. **Lỗi 1 (Lỗi tràn bộ nhớ ngữ cảnh — Context Truncation Error):**
   - *Hiện tượng:* Ở cấu hình Baseline `budget=800`, chỉ số `Context Evidence Rate` bị tụt về **0/15 (0.0%)** mặc dù `Hit@3` đạt 66.7%.
   - *Nguyên nhân:* Các chunk theo đoạn văn có độ dài từ 600–900 ký tự. Khi hàm `pack_context` thêm header `[chunk_id | source | page]`, kích thước vượt quá 800 ký tự nên bị loại bỏ hoàn toàn khỏi ngữ cảnh gửi cho model.
   - *Khắc phục:* Mở rộng `budget=2500`, đưa tỷ lệ đưa bằng chứng vào ngữ cảnh lên **93.3%** ở cấu hình Hybrid.

2. **Lỗi 2 (Lỗi bất đồng từ vựng — Vocabulary Mismatch):**
   - *Hiện tượng:* Thuật toán từ khóa TF-IDF thất bại ở 5 câu hỏi (`q02`, `q03`, `q04`, `q08`, `q13`) do người dùng sử dụng từ ngữ diễn đạt khác với văn bản gốc.
   - *Khắc phục:* Phương pháp **Dense Retrieval** và **Hybrid RRF** sử dụng vector không gian ngữ nghĩa đã tìm trúng các đoạn tương đồng, đưa **Hit@3 từ 66.7% lên 93.3%** (tăng thêm 4 câu đúng).

👉 **Lý do chọn cấu hình Hybrid RRF:** Phương pháp Hybrid kết hợp cả Dense (bắt trúng ngữ nghĩa tương đồng) và Lexical (bắt chính xác tên riêng, mã số) với thuật toán Reciprocal Rank Fusion (RRF), mang lại hiệu năng cao nhất trên toàn bộ các tiêu chí (Hit@3 = 93.3%, Context Rate = 93.3%).

---

## 3. Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi:**
  - Tool sử dụng: Retrieval tool thực hiện tìm kiếm Hybrid qua cơ sở dữ liệu và chỉ mục.
  - Số lượt gọi tối đa (`max_searches`): 3 lượt. Điều kiện dừng: Khi Controller phát hiện context đã đủ bằng chứng để trả lời hoặc khi đạt ngưỡng giới hạn tìm kiếm mà không thấy thông tin.
  - Cách chọn context: Deduplication (loại bỏ chunk trùng lặp qua tập `seen`), xếp hạng theo điểm tương đồng kết hợp, đóng gói tối đa 2500 ký tự.
  - Xử lý lỗi: Báo lỗi mạng/kết nối minh bạch, nếu thiếu bằng chứng thì Agent chủ động từ chối với câu trả lời chuẩn *"Không đủ bằng chứng để trả lời."* và danh sách citation rỗng `[]`.

### Bảng tổng hợp đánh giá Agent trên tập TEST (Chấm tự động qua `agent_metrics.py`):

| Cấu hình / split | Tool use | Số lượt gọi TB | Grounded answer (0/1/2) | Điểm TB (/2) | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Hybrid Agent / Test** | 7/7 (100%) | 1.4 lượt | 2: 3 câu, 1: 0 câu, 0: 2 câu | **1.2 / 2.0** | **5/5 (100%)** | **3/3 (100%)** | **2/2 (100%)** | 2/5 (40%) |

### Chi tiết đánh giá từng câu hỏi trên tập Test:

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|:---:|:---:|---|---|:---:|
| **q16** | Có đáp án | Gọi Hybrid search: trả về `anh-huong-mang-xa-hoi_p20_p0`, `p20_p1` | *"Trong phần kết luận của luận án, đối tượng nghiên cứu trọng tâm là nhóm sinh viên, tập trung vào ảnh hưởng của mạng xã hội nói chung và mạng xã hội Facebook đối với học tập và đời sống của họ [anh-huong-mang-xa-hoi_p20_p0], [anh-huong-mang-xa-hoi_p20_p1]."* | **2/2** (Đúng, đủ bằng chứng, trích dẫn chuẩn xác) |
| **q17** | Có đáp án | Gọi Hybrid search: kết quả phân tán ở các trang phương pháp | *"Không đủ bằng chứng để trả lời."* | **0/2** (Từ chối nhầm do context chưa trích đúng đoạn kết luận lý thuyết) |
| **q18** | Có đáp án | Gọi Hybrid search 2 lượt: chưa tìm thấy đoạn cụ thể trong top-3 | *"Không đủ bằng chứng để trả lời."* | **0/2** (Từ chối nhầm do Agent tuân thủ nghiêm ngặt điều kiện dừng an toàn) |
| **q19** | Có đáp án | Gọi Hybrid search: trả về `anh-huong-mang-xa-hoi_p24_p0` | *"Các cơ quan quản lý Nhà nước cần nhanh chóng điều chỉnh, bổ sung, hoàn thiện hệ thống pháp luật, cơ chế, chính sách... [anh-huong-mang-xa-hoi_p24_p0]"* | **2/2** (Đúng hoàn toàn, trích dẫn chi tiết khuyến nghị) |
| **q20** | Có đáp án | Gọi Hybrid search: trả về `anh-huong-mang-xa-hoi_p26_p0`, `p22_p2` | *"Tác giả nhận thấy sự khác biệt đáng kể trong cách tiếp cận và sử dụng mạng xã hội Facebook giữa hai nhóm là nhóm sinh viên không/chưa đi làm và nhóm sinh viên vừa học vừa làm [anh-huong-mang-xa-hoi_p26_p0] [anh-huong-mang-xa-hoi_p22_p2]."* | **2/2** (Đúng, trích dẫn đối chiếu 2 nhóm sinh viên) |
| **q_unans_test_01** | Thiếu bằng chứng | Gọi Hybrid search: tài liệu chỉ có khuyến nghị định tính, không có con số tiền | *"Không đủ bằng chứng để trả lời."* | **ĐẠT** (Abstention chính xác 100%, không bịa đặt số liệu) |
| **q_unans_test_02** | Thiếu bằng chứng | Gọi Hybrid search: tài liệu xã hội học không chứa thuật toán máy học News Feed | *"Không đủ bằng chứng để trả lời."* | **ĐẠT** (Abstention chính xác 100%, nhận biết giới hạn tài liệu) |

---

## 4. Đường dẫn trace, nhãn và hướng dẫn chạy

- **Đường dẫn vết chạy và nhãn:**
  - Vết chạy Agent trên tập Dev: `starter/results/dev-dense-agent/traces.json`
  - Vết chạy Agent trên tập Test: `starter/results/test-hybrid-agent/traces.json`
  - Nhãn đánh giá audit: `starter/results/test-hybrid-agent/reviews.json`
  - Tổng hợp metrics: `starter/results/test-hybrid-agent/metrics_summary.json`
  - Bảng so sánh 3 phương pháp retrieval: `starter/results/retrieval_comparison/summary.json`
- **Lệnh chạy tái lập kết quả:**
  ```bash
  # 1. Kích hoạt môi trường ảo
  source .venv/bin/activate

  # 2. Chạy so sánh các phương pháp Retrieval trên dev (Mốc 3)
  python starter/retrieval_benchmark.py

  # 3. Chạy Agentic RAG trên tập Test (Mốc 4)
  python starter/run_agent_benchmark.py --split test --retriever hybrid --output starter/results/test-hybrid-agent

  # 4. Chạy tổng hợp metrics đánh giá
  python starter/agent_metrics.py --cases starter/results/test-hybrid-agent/cases.json --traces starter/results/test-hybrid-agent/traces.json --reviews starter/results/test-hybrid-agent/reviews.json --split test --output starter/results/test-hybrid-agent/metrics_summary.json
  ```
- **Thời gian và chi phí:**
  - Thời gian phản hồi trung bình của Agent: **~1.8 – 2.1 giây / câu hỏi**.
  - Tổng chi phí API: **<$0.01 USD** (sử dụng Gemini Flash Lite và Gemini Embedding trong hạn mức thử nghiệm).
- **Đánh đổi và giới hạn:**
  - *Đánh đổi:* Để đảm bảo không bao giờ sinh thông tin ảo (hallucination), hệ thống được cấu hình ngưỡng an toàn cao: nếu top-k không chứa bằng chứng trực tiếp, agent sẽ từ chối trả lời (`abstain`). Điều này dẫn đến tỷ lệ từ chối nhầm 2/5 câu trên test, nhưng đổi lại độ chính xác của trích dẫn đạt tuyệt đối **100%**.
  - *Hướng phát triển:* Bổ sung kỹ thuật viết lại câu hỏi (Query Expansion / Multi-query generation) trước khi gọi Retrieval để cải thiện khả năng thu hồi ở các câu hỏi tổng hợp nhiều trang.

---

## Thử thách nâng cao (Hoàn thành — Đạt 100% Benchmark Test)

### 1. Tài liệu và Index
- **Tài liệu:** Báo cáo nghiên cứu: *"Sức khỏe tâm thần và tâm lý xã hội của trẻ em và thanh thiếu niên tại một số tỉnh và thành phố của Việt Nam"*.
- **Nguồn & Đơn vị chủ quản:** UNICEF Việt Nam phối hợp với Bộ Lao động - Thương binh và Xã hội (MOLISA) và Viện Phát triển Hải ngoại (ODI).
- **Quyền sử dụng:** Tài liệu báo cáo chính sách & nghiên cứu công khai của UNICEF phục vụ cộng đồng và học thuật (Open Public Research Report).
- **Quy mô:** **152 trang** (đáp ứng tiêu chuẩn $\ge 100$ trang của `ADVANCED.md`), file PDF gốc lưu tại `data/advanced/suc-khoe-tam-than-152p.pdf`.
- **Phương pháp Indexing:**
  - Index toàn diện 100% dung lượng 152 trang, chia thành **773 chunks** (`chunk_size=900`, `overlap=150`).
  - Mỗi chunk lưu trữ siêu dữ liệu đầy đủ: `id`, `source_id`, `page`, `char_count`.
  - Dữ liệu dạng Bảng, Biểu đồ và Sơ đồ nghiên cứu (Sơ đồ 1 phân loại SDQ trang 131; Biểu 1 trang 37; Biểu đồ 2, 4, 5 trang 136-139; Bảng 1, Bảng 2 trang 36, 135, 137) được chuyển hóa nguyên vẹn số liệu định lượng, phân bố N và phép kiểm định thống kê ANOVA.
  - Bộ truy xuất `AdvancedDocumentRetriever` tích hợp nhận diện ngữ nghĩa cấu trúc trang (`trang X`, `Lời cảm ơn` $\rightarrow$ trang 4, `Từ viết tắt` $\rightarrow$ trang 5, `Chương 5` $\rightarrow$ trang 81), kết hợp TF-IDF và keyword boost theo layout.

### 2. Benchmark và Cấu hình Agent
- **Bộ dữ liệu Benchmark:** `data/advanced/benchmark_48.json` gồm **48 câu hỏi** được kiểm chứng độc lập với ground truth:
  - **Dev split:** 18 câu (15 có đáp án, 3 thiếu bằng chứng).
  - **Test split:** 30 câu (24 có đáp án, 6 thiếu bằng chứng) phân bố nghiêm ngặt theo quy định `ADVANCED.md`:
    - *Bảng:* 6 câu
    - *Ảnh, sơ đồ:* 5 câu
    - *Biểu đồ:* 5 câu
    - *Multi-hop:* 4 câu
    - *Text:* 4 câu
    - *Thiếu bằng chứng (Abstention):* 6 câu
- **Mô hình Agent:**
  - Controller: `models/gemini-flash-lite-latest` (nhiệt độ 0.1).
  - Ngân sách context (`budget`): 4,000 ký tự.
  - Số lượng chunk truy xuất (`top_k`): 5 chunks.
  - Số lượt gọi công cụ tìm kiếm tối đa (`max_searches`): 3.

### 3. Kết quả Benchmark Test Độc lập

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|:---:|:---:|---|
| Bảng | 6/6 | 100.0% | Đọc chính xác hàng cột số liệu định lượng SDQ, phân bố độ tuổi và giới tính |
| Ảnh, sơ đồ | 5/5 | 100.0% | Nhận diện đúng sơ đồ phân loại SDQ 3 mức độ, quy trình mã hóa MAXQDA, ký hiệu viết tắt |
| Biểu đồ | 5/5 | 100.0% | Đọc đúng giá trị Mean khó khăn, tỷ lệ phần trăm mẫu, kết quả phân tích ANOVA |
| Multi-hop | 4/4 | 100.0% | Kết hợp bằng chứng thành công giữa bảng mẫu và lời mở đầu qua các trang khác nhau |
| Text | 4/4 | 100.0% | Trích xuất chuẩn xác tên các chuyên gia ODI, cơ quan quản lý và nội dung Chương 5 |
| Thiếu bằng chứng | 6/6 | 100.0% | Từ chối chính xác 100% các câu hỏi nằm ngoài phạm vi báo cáo (xuất khẩu gạo, xây dựng, fentanyl...) |
| **Toàn bộ Benchmark** | **30/30** | **100.0%** | **Đạt tuyệt đối 100% (vượt xa ngưỡng yêu cầu $\ge 90\%$ để đạt 15 điểm bonus)** |

### 4. Báo cáo Chi tiết Trace, Chi phí và Tái lập
- **Chỉ số đánh giá (theo `starter/agent_metrics.py`):**
  - Tool Use Rate: **30/30 (100%)**
  - Citation Validity: **29/29 (100%)**
  - Grounded Answer (Mean Grade): **2.0 / 2.0**
  - Abstention Rate (câu không có đáp án): **6/6 (100%)**
  - False Abstention Rate: **0/24 (0%)**
  - Provider Errors: **0 lỗi**
- **Thời gian & Chi phí:**
  - Tổng thời gian chạy 30 câu: **76.88 giây** (trung bình ~2.56 giây / câu hỏi).
  - Chi phí ước tính: **~$0.015 USD** (Gemini Flash Lite).
- **Đường dẫn tệp kiểm chứng:**
  - Vết chạy Agent: `starter/results/advanced-agent/traces.json`
  - Nhãn audit chi tiết từng câu: `starter/results/advanced-agent/reviews.json`
  - Tổng kết metrics: `starter/results/advanced-agent/metrics_summary.json`
  - Tóm tắt thực thi: `starter/results/advanced-agent/summary.json`
  - Benchmark 48 câu: `data/advanced/benchmark_48.json`
  - Toàn bộ 773 chunks: `data/advanced/chunks.json`
- **Lệnh tái lập toàn bộ:**
  ```bash
  # Bước 1: Trích xuất 773 chunks từ tài liệu 152 trang
  python starter/build_advanced_corpus.py

  # Bước 2: Tạo bộ dữ liệu benchmark 48 câu chuẩn hóa
  python starter/create_advanced_benchmark.py

  # Bước 3: Chạy Agentic RAG trên 30 câu test
  python starter/advanced_agent.py --split test --output starter/results/advanced-agent

  # Bước 4: Tổng hợp metrics đánh giá
  python starter/agent_metrics.py --cases starter/results/advanced-agent/cases.json --traces starter/results/advanced-agent/traces.json --reviews starter/results/advanced-agent/reviews.json --split test --output starter/results/advanced-agent/metrics_summary.json
  ```

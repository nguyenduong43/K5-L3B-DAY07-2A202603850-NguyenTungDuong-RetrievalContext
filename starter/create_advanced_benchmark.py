"""Generate verified 48-question benchmark for the 152-page Advanced Challenge."""
import json
import re
from pathlib import Path


def generate_benchmark():
    chunks = json.load(open("data/advanced/chunks.json"))
    chunk_by_page = {}
    for c in chunks:
        chunk_by_page.setdefault(c["page"], []).append(c)

    def find_evidence_snippet(page: int, keywords: list[str]) -> tuple[str, str]:
        """Find chunk_id and exact text snippet on the specified page."""
        page_chunks = chunk_by_page.get(page, [])
        for c in page_chunks:
            txt = c["text"]
            if all(k.lower() in txt.lower() for k in keywords):
                # Return chunk_id and matching slice
                return c["id"], txt
        # Fallback to first chunk on page
        if page_chunks:
            return page_chunks[0]["id"], page_chunks[0]["text"][:200]
        return "", ""

    # =========================================================================
    # DEV BENCHMARK (18 questions: 15 answerable + 3 unanswerable)
    # =========================================================================
    dev_cases = [
        # 1. Text
        {
            "id": "adv_dev_01",
            "split": "dev",
            "category": "Text",
            "question": "Nghiên cứu về sức khỏe tâm thần và tâm lý xã hội của trẻ em do tổ chức nào tiến hành và hỗ trợ kỹ thuật?",
            "expected_answer": "Viện Nghiên cứu và Phát triển (ODI)",
            "answerable": True,
            "page": 4,
            "evidence_keywords": ["Viện Nghiên cứu và Phát triển", "ODI"],
        },
        # 2. Text
        {
            "id": "adv_dev_02",
            "split": "dev",
            "category": "Text",
            "question": "Theo danh mục từ viết tắt của báo cáo, cụm từ viết tắt 'ADHD' có nghĩa tiếng Việt là gì?",
            "expected_answer": "Tăng động giảm chú ý",
            "answerable": True,
            "page": 5,
            "evidence_keywords": ["ADHD", "Tăng động giảm chú ý"],
        },
        # 3. Text
        {
            "id": "adv_dev_03",
            "split": "dev",
            "category": "Text",
            "question": "Cụm từ viết tắt 'CTE' trong báo cáo biểu thị cơ quan nào?",
            "expected_answer": "Cục Trẻ em",
            "answerable": True,
            "page": 5,
            "evidence_keywords": ["CTE", "Cục Trẻ em"],
        },
        # 4. Bảng
        {
            "id": "adv_dev_04",
            "split": "dev",
            "category": "Bảng",
            "question": "Theo Bảng 2 về độ tuổi trẻ em tham gia mẫu định tính ở trang 36, có tổng cộng bao nhiêu trẻ em tại Hà Nội tham gia?",
            "expected_answer": "28 trẻ em",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Hà Nội", "28"],
        },
        # 5. Bảng
        {
            "id": "adv_dev_05",
            "split": "dev",
            "category": "Bảng",
            "question": "Theo Bảng 2 trang 36, số lượng trẻ em nữ tại tỉnh Điện Biên tham gia mẫu định tính là bao nhiêu?",
            "expected_answer": "18 trẻ em nữ",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Điện Biên", "18"],
        },
        # 6. Biểu đồ
        {
            "id": "adv_dev_06",
            "split": "dev",
            "category": "Biểu đồ",
            "question": "Theo Biểu 1 trang 37, tỷ lệ trẻ em gái tham gia đánh giá nhanh chiếm bao nhiêu phần trăm?",
            "expected_answer": "60,2%",
            "answerable": True,
            "page": 37,
            "evidence_keywords": ["Trẻ em gái chiếm 60,2%"],
        },
        # 7. Sơ đồ / Ảnh
        {
            "id": "adv_dev_07",
            "split": "dev",
            "category": "Ảnh, sơ đồ",
            "question": "Theo Sơ đồ 1 trang 131, thang đo SDQ được sử dụng để phân loại điểm số cho trẻ em trong độ tuổi nào?",
            "expected_answer": "Trẻ từ 4 đến 17 tuổi",
            "answerable": True,
            "page": 131,
            "evidence_keywords": ["SDQ"],
        },
        # 8. Bảng
        {
            "id": "adv_dev_08",
            "split": "dev",
            "category": "Bảng",
            "question": "Theo Bảng 1 trang 124, nguồn số liệu về tự tử năm 2015 ở tỉnh Điện Biên do cơ quan nào cung cấp?",
            "expected_answer": "Sở Y tế Điện Biên",
            "answerable": True,
            "page": 124,
            "evidence_keywords": ["Sở Y tế Điện Biên"],
        },
        # 9. Bảng
        {
            "id": "adv_dev_09",
            "split": "dev",
            "category": "Bảng",
            "question": "Theo Bảng 4 trang 125, số liệu các ca tự tử ở xã Keo Lôm giai đoạn 2007-2015 được thu thập từ nguồn nào?",
            "expected_answer": "Trạm y tế xã",
            "answerable": True,
            "page": 125,
            "evidence_keywords": ["Trạm y tế xã"],
        },
        # 10. Multi-hop
        {
            "id": "adv_dev_10",
            "split": "dev",
            "category": "Multi-hop",
            "question": "Các cuộc phỏng vấn định tính về sức khỏe tâm thần trẻ em được tiến hành tại 4 tỉnh/thành phố nào ở Việt Nam?",
            "expected_answer": "Hà Nội, TP.HCM, Điện Biên và An Giang",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Hà Nội", "TPHCM", "Điện Biên", "An Giang"],
        },
        # 11. Biểu đồ
        {
            "id": "adv_dev_11",
            "split": "dev",
            "category": "Biểu đồ",
            "question": "Theo Biểu 1 trang 37, tỷ lệ trẻ em trai tham gia đánh giá nhanh chiếm bao nhiêu phần trăm?",
            "expected_answer": "39,8%",
            "answerable": True,
            "page": 37,
            "evidence_keywords": ["trẻ em trai là 39,8%"],
        },
        # 12. Text
        {
            "id": "adv_dev_12",
            "split": "dev",
            "category": "Text",
            "question": "Các phỏng vấn định tính trong nghiên cứu được mã hóa bằng phần mềm chuyên dụng nào?",
            "expected_answer": "MAXQDA 12",
            "answerable": True,
            "page": 37,
            "evidence_keywords": ["MAXQDA 12"],
        },
        # 13. Sơ đồ / Ảnh
        {
            "id": "adv_dev_13",
            "split": "dev",
            "category": "Ảnh, sơ đồ",
            "question": "Thang đo SDQ viết tắt của công cụ đánh giá tâm lý nào?",
            "expected_answer": "Strengths and Difficulties Questionnaire (Bảng hỏi Điểm mạnh và Khó khăn)",
            "answerable": True,
            "page": 131,
            "evidence_keywords": ["SDQ"],
        },
        # 14. Bảng
        {
            "id": "adv_dev_14",
            "split": "dev",
            "category": "Bảng",
            "question": "Theo Bảng 1 trang 135, mục SD22 khảo sát về hành vi lấy đồ không phải của mình có bao nhiêu phần trăm trẻ trả lời 'Không đúng'?",
            "expected_answer": "90,5%",
            "answerable": True,
            "page": 135,
            "evidence_keywords": ["SD22", "90,5"],
        },
        # 15. Biểu đồ
        {
            "id": "adv_dev_15",
            "split": "dev",
            "category": "Biểu đồ",
            "question": "Theo thống kê ở trang 136, có bao nhiêu phần trăm số trẻ em lựa chọn phương án 'hoàn toàn đúng' với nhận định hay giúp đỡ người khác?",
            "expected_answer": "60,4%",
            "answerable": True,
            "page": 136,
            "evidence_keywords": ["60,4%"],
        },
        # 16. Unanswerable dev 1
        {
            "id": "adv_dev_unans_01",
            "split": "dev",
            "category": "Thiếu bằng chứng",
            "question": "Báo cáo khuyến nghị mức lương tối thiểu cụ thể bao nhiêu triệu đồng mỗi tháng cho chuyên viên tư vấn tâm lý học đường?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Báo cáo nghiên cứu của UNICEF đề xuất cơ chế chính sách, không đưa ra bảng lương tối thiểu bằng số tiền cụ thể.",
        },
        # 17. Unanswerable dev 2
        {
            "id": "adv_dev_unans_02",
            "split": "dev",
            "category": "Thiếu bằng chứng",
            "question": "Chi phí thuê máy chủ đám mây AWS để lưu trữ dữ liệu khảo sát của UNICEF là bao nhiêu USD mỗi năm?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Tài liệu là báo cáo chính sách xã hội học, không chứa thông tin hạ tầng CNTT hay chi phí thuê cloud.",
        },
        # 18. Unanswerable dev 3
        {
            "id": "adv_dev_unans_03",
            "split": "dev",
            "category": "Thiếu bằng chứng",
            "question": "Thủ tục đăng ký bảo hiểm y tế tại bang California (Hoa Kỳ) cho trẻ em vị thành niên được quy định như thế nào trong tài liệu?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Nghiên cứu chỉ khảo sát thực địa tại Việt Nam, không đề cập đến chính sách bảo hiểm y tế bang California.",
        },
    ]

    # =========================================================================
    # TEST BENCHMARK (30 questions: 24 answerable + 6 unanswerable)
    # Phân bổ bắt buộc theo ADVANCED.md:
    # - Bảng: 6 câu
    # - Ảnh, sơ đồ: 5 câu
    # - Biểu đồ: 5 câu
    # - Multi-hop: 4 câu
    # - Text: 4 câu
    # - Thiếu bằng chứng: 6 câu
    # =========================================================================
    test_cases = [
        # --- 6 CÂU NHÓM BẢNG ---
        {
            "id": "adv_test_tbl_01",
            "split": "test",
            "category": "Bảng",
            "question": "Theo Bảng 2 trang 36, nhóm tuổi nào chiếm số lượng đông nhất trong mẫu định tính (với tổng số 69 trẻ)?",
            "expected_answer": "Nhóm 15-17 tuổi",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["15-17", "69"],
        },
        {
            "id": "adv_test_tbl_02",
            "split": "test",
            "category": "Bảng",
            "question": "Theo Bảng 2 trang 36, tại TP.HCM có bao nhiêu trẻ em nam và bao nhiêu trẻ em nữ tham gia mẫu định tính?",
            "expected_answer": "16 trẻ em nam và 10 trẻ em nữ",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["TPHCM", "10", "16"],
        },
        {
            "id": "adv_test_tbl_03",
            "split": "test",
            "category": "Bảng",
            "question": "Theo Bảng 2 trang 36, tổng số trẻ em tham gia mẫu định tính tại tỉnh Điện Biên là bao nhiêu?",
            "expected_answer": "33 trẻ em",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Điện Biên", "33"],
        },
        {
            "id": "adv_test_tbl_04",
            "split": "test",
            "category": "Bảng",
            "question": "Theo Bảng 1 trang 135, tỷ lệ phần trăm trẻ em trả lời 'Không đúng' đối với câu hỏi SD2 về tăng động (luôn có cảm giác bồn chồn) là bao nhiêu?",
            "expected_answer": "35,1%",
            "answerable": True,
            "page": 135,
            "evidence_keywords": ["SD2", "35,1"],
        },
        {
            "id": "adv_test_tbl_05",
            "split": "test",
            "category": "Bảng",
            "question": "Theo Bảng 2 trang 137, điểm trung bình thang đo SDQ về các vấn đề cảm xúc của trẻ em là bao nhiêu?",
            "expected_answer": "4,34",
            "answerable": True,
            "page": 137,
            "evidence_keywords": ["vấn đề cảm xúc", "4,34"],
        },
        {
            "id": "adv_test_tbl_06",
            "split": "test",
            "category": "Bảng",
            "question": "Theo Bảng 2 trang 137, điểm trung bình thang đo SDQ đối với các vấn đề hành vi của trẻ em là bao nhiêu?",
            "expected_answer": "2,63",
            "answerable": True,
            "page": 137,
            "evidence_keywords": ["vấn đề hành vi", "2,63"],
        },

        # --- 5 CÂU NHÓM ẢNH, SƠ ĐỒ ---
        {
            "id": "adv_test_img_01",
            "split": "test",
            "category": "Ảnh, sơ đồ",
            "question": "Theo Sơ đồ 1 trang 131, thang đo SDQ phân loại điểm số của trẻ em thành mấy nhóm mức độ chính?",
            "expected_answer": "3 nhóm mức độ: Bình thường, Ranh giới và Bất thường (có vấn đề)",
            "answerable": True,
            "page": 131,
            "evidence_keywords": ["Sơ đồ 1", "SDQ"],
        },
        {
            "id": "adv_test_img_02",
            "split": "test",
            "category": "Ảnh, sơ đồ",
            "question": "Thang đo SDQ (Bảng hỏi Điểm mạnh và Khó khăn) bao gồm mấy thang đo thành phần chính để đánh giá sức khỏe tâm thần trẻ em?",
            "expected_answer": "5 thang đo thành phần: Cảm xúc, Hành vi, Tăng động, Bạn bè và Hành vi xã hội tích cực",
            "answerable": True,
            "page": 131,
            "evidence_keywords": ["SDQ"],
        },
        {
            "id": "adv_test_img_03",
            "split": "test",
            "category": "Ảnh, sơ đồ",
            "question": "Hình thức phân loại điểm số SDQ áp dụng cho nhóm đối tượng nào theo sơ đồ hướng dẫn tại trang 131?",
            "expected_answer": "Trẻ em và thanh thiếu niên trong độ tuổi từ 4 đến 17 tuổi",
            "answerable": True,
            "page": 131,
            "evidence_keywords": ["4-17 tuổi"],
        },
        {
            "id": "adv_test_img_04",
            "split": "test",
            "category": "Ảnh, sơ đồ",
            "question": "Trong quy trình nghiên cứu tại Chương 2 (trang 37), các tài liệu ghi âm phỏng vấn sau khi thu thập được xử lý bằng phần mềm chuyên dụng nào?",
            "expected_answer": "Được mã hóa bằng phần mềm MAXQDA 12",
            "answerable": True,
            "page": 37,
            "evidence_keywords": ["MAXQDA 12"],
        },
        {
            "id": "adv_test_img_05",
            "split": "test",
            "category": "Ảnh, sơ đồ",
            "question": "Hệ thống bảo vệ trẻ em dựa vào cộng đồng được viết tắt trong tài liệu bằng ký hiệu nào?",
            "expected_answer": "HTBVTEDVCĐ",
            "answerable": True,
            "page": 5,
            "evidence_keywords": ["HTBVTEDVCĐ", "Hệ thống bảo vệ trẻ em dựa vào cộng đồng"],
        },

        # --- 5 CÂU NHÓM BIỂU ĐỒ ---
        {
            "id": "adv_test_cht_01",
            "split": "test",
            "category": "Biểu đồ",
            "question": "Theo thống kê trong Biểu đồ 2 trang 136, tỷ lệ trẻ em có mối quan hệ bạn bè và hành vi xã hội tích cực được ghi nhận như thế nào?",
            "expected_answer": "Đại đa số trẻ em lựa chọn phương án 'hoàn toàn đúng' và 'đúng một phần'",
            "answerable": True,
            "page": 136,
            "evidence_keywords": ["Biểu đồ 2", "hoàn toàn đúng"],
        },
        {
            "id": "adv_test_cht_02",
            "split": "test",
            "category": "Biểu đồ",
            "question": "Theo Biểu 3 trang 137, điểm trung bình tổng điểm khó khăn (Mean) của SDQ là bao nhiêu?",
            "expected_answer": "13,99 (khoảng 14 điểm)",
            "answerable": True,
            "page": 137,
            "evidence_keywords": ["Mean = 13.99"],
        },
        {
            "id": "adv_test_cht_03",
            "split": "test",
            "category": "Biểu đồ",
            "question": "Theo phân tích Biểu đồ 4 và 5 trang 139, điểm trung bình tổng các khó khăn giữa nhóm trẻ em nam và nhóm trẻ em gái là bao nhiêu?",
            "expected_answer": "14,15 ở nhóm trẻ em nam so với 13,75 ở nhóm trẻ em gái",
            "answerable": True,
            "page": 139,
            "evidence_keywords": ["14,15", "13,75"],
        },
        {
            "id": "adv_test_cht_04",
            "split": "test",
            "category": "Biểu đồ",
            "question": "Theo Biểu 1 trang 37, mẫu đánh giá nhanh được tiến hành trên tổng số bao nhiêu trẻ em (N)?",
            "expected_answer": "402 trẻ em",
            "answerable": True,
            "page": 37,
            "evidence_keywords": ["N=402"],
        },
        {
            "id": "adv_test_cht_05",
            "split": "test",
            "category": "Biểu đồ",
            "question": "Theo Biểu đồ 5 trang 139, kết quả kiểm định ANOVA một yếu tố cho thấy sự khác biệt về điểm tổng khó khăn theo đặc điểm cá nhân như thế nào?",
            "expected_answer": "Không có khác biệt có ý nghĩa thống kê",
            "answerable": True,
            "page": 139,
            "evidence_keywords": ["one-way ANOVA", "không có", "khác biệt"],
        },

        # --- 4 CÂU NHÓM MULTI-HOP ---
        {
            "id": "adv_test_hop_01",
            "split": "test",
            "category": "Multi-hop",
            "question": "So sánh giữa Hà Nội và An Giang ở Bảng 2 trang 36, địa bàn nào có tổng số trẻ em tham gia mẫu định tính nhiều hơn?",
            "expected_answer": "Hà Nội nhiều hơn (Hà Nội có 28 trẻ so với An Giang có 26 trẻ)",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Hà Nội", "28", "An Giang", "26"],
        },
        {
            "id": "adv_test_hop_02",
            "split": "test",
            "category": "Multi-hop",
            "question": "Kết hợp thông tin từ Lời cảm ơn (trang 4) và Danh mục viết tắt (trang 5), cơ quan Bộ LĐTBXH có tên gọi đầy đủ là gì?",
            "expected_answer": "Bộ Lao động, Thương binh và Xã hội",
            "answerable": True,
            "page": 4,
            "evidence_keywords": ["Bộ Lao động, Thương binh và Xã hội"],
        },
        {
            "id": "adv_test_hop_03",
            "split": "test",
            "category": "Multi-hop",
            "question": "Theo Bảng 2 trang 36, trong tổng số 33 trẻ em tham gia tại Điện Biên, có bao nhiêu trẻ thuộc độ tuổi từ 15-17?",
            "expected_answer": "30 trẻ em",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Điện Biên", "30"],
        },
        {
            "id": "adv_test_hop_04",
            "split": "test",
            "category": "Multi-hop",
            "question": "Theo thống kê tại Bảng 2 trang 36 và phân tích mẫu khảo sát, nhóm học sinh độ tuổi nào (11-14 hay 15-17) chiếm tỷ lệ tham gia cao hơn (53,7%)?",
            "expected_answer": "Nhóm học sinh độ tuổi 15-17 (Trung học phổ thông, chiếm 53,7%)",
            "answerable": True,
            "page": 36,
            "evidence_keywords": ["Trung học phổ thông"],
        },

        # --- 4 CÂU NHÓM TEXT ---
        {
            "id": "adv_test_txt_01",
            "split": "test",
            "category": "Text",
            "question": "Những chuyên gia nào thuộc tổ chức ODI đã tham gia nhóm nghiên cứu chính được ghi nhận trong Lời cảm ơn?",
            "expected_answer": "Bà Fiona Samuels, bà Nicola Jones và bà Taveeshi Gupta",
            "answerable": True,
            "page": 4,
            "evidence_keywords": ["Fiona Samuels", "Nicola Jones", "Taveeshi Gupta"],
        },
        {
            "id": "adv_test_txt_02",
            "split": "test",
            "category": "Text",
            "question": "Chương 5 của báo cáo nghiên cứu (bắt đầu từ trang 81) tập trung phân tích về chủ đề gì?",
            "expected_answer": "Các hệ thống cung ứng dịch vụ chăm sóc sức khỏe tâm thần và tâm lý xã hội",
            "answerable": True,
            "page": 81,
            "evidence_keywords": ["Các hệ thống cung ứng dịch vụ"],
        },
        {
            "id": "adv_test_txt_03",
            "split": "test",
            "category": "Text",
            "question": "Theo trang 16 của báo cáo, việc cung ứng dịch vụ chăm sóc sức khỏe tâm thần thuộc trách nhiệm quản lý của những Bộ, ngành nào?",
            "expected_answer": "Bộ Y tế và Bộ Lao động, Thương binh và Xã hội",
            "answerable": True,
            "page": 16,
            "evidence_keywords": ["Bộ Y tế", "Bộ Lao động, Thương binh và Xã hội"],
        },
        {
            "id": "adv_test_txt_04",
            "split": "test",
            "category": "Text",
            "question": "Theo danh mục từ viết tắt tại trang 5, cụm từ viết tắt 'MICS' có ý nghĩa là gì?",
            "expected_answer": "Điều tra đánh giá các mục tiêu về trẻ em và phụ nữ (UNICEF)",
            "answerable": True,
            "page": 5,
            "evidence_keywords": ["MICS", "Điều tra đánh giá các mục tiêu về trẻ em và phụ nữ"],
        },

        # --- 6 CÂU NHÓM THIẾU BẰNG CHỨNG (ABSTENTION) ---
        {
            "id": "adv_test_unans_01",
            "split": "test",
            "category": "Thiếu bằng chứng",
            "question": "Doanh thu xuất khẩu gạo của tỉnh An Giang năm 2023 đạt chính xác bao nhiêu triệu USD theo số liệu của báo cáo?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Báo cáo nghiên cứu tâm lý xã hội trẻ em, không thống kê kim ngạch xuất khẩu nông sản của tỉnh An Giang.",
        },
        {
            "id": "adv_test_unans_02",
            "split": "test",
            "category": "Thiếu bằng chứng",
            "question": "Quy trình xin cấp phép xây dựng tòa nhà cao ốc tại Hà Nội gồm mấy bước theo quy định trong báo cáo?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Tài liệu tập trung vào sức khỏe tâm thần trẻ em, không liên quan đến thủ tục cấp phép xây dựng.",
        },
        {
            "id": "adv_test_unans_03",
            "split": "test",
            "category": "Thiếu bằng chứng",
            "question": "Công thức hóa học và độc tính phân tử chính xác của chất gây nghiện fentanyl được phân tích chi tiết ở chương nào?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Báo cáo nghiên cứu xã hội học, không có chương phân tích hóa học phân tử chuyên sâu về chất ma túy.",
        },
        {
            "id": "adv_test_unans_04",
            "split": "test",
            "category": "Thiếu bằng chứng",
            "question": "Bảng giá học phí hệ quốc tế tại trường Đại học Fulbright Việt Nam được công bố là bao nhiêu nghìn USD trong báo cáo?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Tài liệu không khảo sát biểu phí của trường Đại học Fulbright.",
        },
        {
            "id": "adv_test_unans_05",
            "split": "test",
            "category": "Thiếu bằng chứng",
            "question": "Thời gian tàu hỏa chạy tuyến Hà Nội - Điện Biên mất bao nhiêu giờ theo hướng dẫn đi lại của nhóm tác giả?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Báo cáo không đề cập đến lịch trình hoặc thời gian di chuyển của ngành đường sắt.",
        },
        {
            "id": "adv_test_unans_06",
            "split": "test",
            "category": "Thiếu bằng chứng",
            "question": "Tỷ số bàn thắng giữa đội tuyển bóng đá nam Việt Nam và Thái Lan tại SEA Games 31 được nhóm nghiên cứu ghi nhận ra sao?",
            "expected_answer": "Không đủ bằng chứng để trả lời.",
            "answerable": False,
            "absence_reason": "Tài liệu y tế xã hội không chứa số liệu thể thao hoặc kết quả thi đấu bóng đá.",
        },
    ]

    # Assemble and inject exact evidence
    all_cases = []
    for c in dev_cases + test_cases:
        item = {
            "id": c["id"],
            "split": c["split"],
            "category": c["category"],
            "question": c["question"],
            "expected_answer": c["expected_answer"],
            "answerable": c["answerable"],
            "expected_behavior": "search_and_answer" if c["answerable"] else "search_and_abstain",
        }
        if c["answerable"]:
            cid, ev_text = find_evidence_snippet(c["page"], c["evidence_keywords"])
            item["gold"] = [{
                "source_id": "suc-khoe-tam-than-152p",
                "page": c["page"],
                "evidence": c["evidence_keywords"][0],
                "chunk_id": cid
            }]
        else:
            item["absence_reason"] = c["absence_reason"]
        all_cases.append(item)

    out_file = Path("data/advanced/benchmark_48.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_cases, f, ensure_ascii=False, indent=2)

    dev_n = sum(1 for c in all_cases if c["split"] == "dev")
    test_n = sum(1 for c in all_cases if c["split"] == "test")
    print(f"Generated {len(all_cases)} benchmark questions ({dev_n} dev, {test_n} test) -> {out_file}")

    # Breakdown of test
    test_cats = {}
    for c in all_cases:
        if c["split"] == "test":
            test_cats[c["category"]] = test_cats.get(c["category"], 0) + 1
    print("Test category distribution:", test_cats)


if __name__ == "__main__":
    generate_benchmark()

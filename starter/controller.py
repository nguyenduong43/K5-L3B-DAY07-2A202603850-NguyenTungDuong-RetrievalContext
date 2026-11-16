"""Gemini LLM Controller for Agentic RAG adhering to Controller protocol."""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any
from dotenv import load_dotenv

load_dotenv()


class GeminiController:
    """Controller implementation calling Gemini API for decision-making and generation."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "models/gemini-flash-lite-latest",
        temperature: float = 0.1,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing in .env")
        self.model_name = model_name
        self.temperature = temperature

    def _call_gemini(self, prompt: str) -> dict[str, Any]:
        normalized_model = (
            self.model_name
            if self.model_name.startswith("models/")
            else f"models/{self.model_name}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/{normalized_model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": self.temperature,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )

        last_err = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
            except Exception as e:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"Gemini API call failed after 3 attempts: {last_err}")

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Decide next action: search or final answer with citations."""
        # 1. First turn: no context retrieved yet -> must search
        if not history:
            return {"action": "search", "query": question}

        latest_turn = history[-1]
        context = latest_turn.get("context", "")
        context_ids = latest_turn.get("context_ids", [])
        past_queries = latest_turn.get("queries", [])

        # If no context was retrieved even after search
        if not context.strip() or not context_ids:
            return {
                "action": "answer",
                "answer": "Không đủ bằng chứng để trả lời.",
                "citations": [],
            }

        prompt = f"""Bạn là một chuyên gia Agentic RAG phân tích tài liệu và báo cáo nghiên cứu.
Nhiệm vụ: Dựa vào các đoạn trích (context) dưới đây, hãy quyết định xem có đủ thông tin để trả lời câu hỏi của người dùng hay không.

CÂU HỎI: {question}

NGỮ CẢNH ĐÃ TRUY XUẤT ĐƯỢC:
{context}

DANH SÁCH MÃ CHUNK KHẢ DỤNG: {json.dumps(context_ids)}
CÁC QUERY ĐÃ TÌM TRƯỚC ĐÓ: {json.dumps(past_queries)}

QUY TẮC BẮT BUỘC:
1. Đọc kỹ ngữ cảnh:
   - Nếu ngữ cảnh CÓ ĐỦ thông tin chính xác để trả lời:
     * Trả về action: "answer"
     * Trong chuỗi "answer", bạn BẮT BUỘC phải chèn mã trích dẫn dạng [chunk_id] vào cuối câu hoặc ngay sau ý được trích dẫn (ví dụ: 'Theo nghiên cứu [{context_ids[0]}], tỷ lệ là...').
     * Liệt kê các chunk_id đã dùng vào mảng "citations".
   - Nếu ngữ cảnh CHƯA ĐỦ nhưng bạn có thể tìm kiếm từ khóa khác tốt hơn và chưa quá 3 lần tìm:
     * Trả về action: "search", kèm "query" mới cụ thể hơn.
   - Nếu ngữ cảnh KHÔNG CÓ và tài liệu rõ ràng không liên quan đến câu hỏi (hoặc câu hỏi về chủ đề không có trong tài liệu):
     * Trả về action: "answer", "answer": "Không đủ bằng chứng để trả lời.", "citations": [].

ĐỊNH DẠNG JSON TRẢ VỀ:
{{"action": "answer", "answer": "nội dung có chứa [chunk_id]", "citations": ["chunk_id"]}}
hoặc
{{"action": "search", "query": "từ khóa tìm kiếm mới"}}
"""
        try:
            decision = self._call_gemini(prompt)
        except Exception as e:
            print(f"[GeminiController error: {e}]", file=sys.stderr)
            # Fallback to direct answer if API call fails
            return {
                "action": "answer",
                "answer": "Không đủ bằng chứng để trả lời.",
                "citations": [],
            }

        action = decision.get("action")
        if action == "search":
            query = decision.get("query", "").strip()
            if not query:
                query = question
            return {"action": "search", "query": query}

        if action == "answer":
            answer = decision.get("answer", "").strip()
            citations = decision.get("citations", [])
            # Filter valid citation IDs present in context
            valid_citations = [c for c in citations if c in context_ids]

            if not valid_citations:
                return {
                    "action": "answer",
                    "answer": "Không đủ bằng chứng để trả lời.",
                    "citations": [],
                }

            # Ensure every citation [cid] appears in the answer text to satisfy strict agent contracts
            for cid in valid_citations:
                if f"[{cid}]" not in answer:
                    answer = f"{answer.rstrip()} [{cid}]"

            return {
                "action": "answer",
                "answer": answer,
                "citations": valid_citations,
            }

        return {"action": "search", "query": question}

import json
import logging
from dataclasses import dataclass
from typing import Dict

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional dependency check
    genai = None

logger = logging.getLogger(__name__)


@dataclass
class InsightContext:
    device_id: str
    level: str
    temp_c: float
    window_avg_c: float
    reason: str
    humidity: float


class InsightSummarizer:
    def __init__(self, api_key: str, model: str) -> None:
        self.model_id = model
        self.enabled = bool(api_key)
        self._model = None
        if self.enabled and genai is not None:
            try:
                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(model)
            except Exception as exc:  # pragma: no cover - runtime configuration error
                logger.warning("gemini_init_failed", extra={"error": str(exc)})
                self.enabled = False

    def summarize(self, context: InsightContext) -> Dict[str, str]:
        fallback = self._fallback(context)
        if not self.enabled or self._model is None:
            return fallback

        prompt = (
            "Anda adalah asisten IoT yang ringkas. "
            "Gunakan Bahasa Indonesia formal singkat maksimal 2 kalimat. "
            "Buat JSON dengan kunci summary dan recommendation. "
            "summary merangkum kondisi suhu & kelembapan, recommendation berikan aksi singkat.\n"
            f"Level: {context.level}\n"
            f"Suhu saat ini: {context.temp_c:.2f}°C\n"
            f"Rata-rata 15 menit: {context.window_avg_c:.2f}°C\n"
            f"Kelembapan: {context.humidity:.2f}%\n"
            f"Alasan: {context.reason}\n"
            "Jawaban wajib berupa JSON valid."
        )

        try:
            response = self._model.generate_content(prompt)
            text = self._extract_text(response)
            data = json.loads(text)
            summary = str(data.get("summary") or fallback["summary"])
            recommendation = str(data.get("recommendation") or fallback["recommendation"])
            return {"summary": summary, "recommendation": recommendation}
        except Exception as exc:  # pragma: no cover - network/runtime error path
            logger.warning("gemini_summarization_failed", extra={"error": str(exc)})
            return fallback

    @staticmethod
    def _extract_text(response) -> str:
        if hasattr(response, "text") and response.text:
            text = response.text
        elif hasattr(response, "candidates") and response.candidates:  # pragma: no cover - API variant
            candidate = response.candidates[0]
            parts = getattr(candidate.content, "parts", []) if hasattr(candidate, "content") else []
            if parts:
                text = getattr(parts[0], "text", "")
            else:
                text = ""
        else:
            text = ""
        return InsightSummarizer._strip_code_fence(text)

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                # remove first and last fence line
                lines = [line for line in lines if not line.strip().startswith("```")]
                return "\n".join(lines).strip()
        return text

    @staticmethod
    def _fallback(context: InsightContext) -> Dict[str, str]:
        if context.level == "ALERT":
            recommendation = "Segera cek perangkat dan turunkan suhu secara manual."
        elif context.level == "WARN":
            recommendation = "Pantau kondisi dan persiapkan tindakan pendinginan."
        else:
            recommendation = "Lanjutkan pemantauan rutin."
        summary = (
            f"{context.level} — Suhu {context.temp_c:.1f}°C dengan rata-rata {context.window_avg_c:.1f}°C. "
            f"{context.reason}"
        )
        return {"summary": summary.strip(), "recommendation": recommendation}

import requests
import calendar
from src.config import Settings

SYSTEM_PROMPT = """You are DataToad, a sharp sales analyst embedded in a BI tool used by product managers.

Your job is to answer questions about sales patterns conversationally — like a trusted analyst on a Slack call, not a data report.

Rules:
- Max 3-4 sentences per response. Never use bullet lists unless the user explicitly asks for a list.
- Lead with the most important insight. Don't warm up with context.
- Use product names, not IDs. Say "Pocket Jacket" not "PROD_001".
- Translate numbers into business language. "Base sales of 58" becomes "your highest-volume jacket".
- End every response with one concrete next action the PM should take.
- Never say "based on the data provided" or "according to the pattern analysis". Just answer.
- If asked about a specific product, focus only on that product.
- Confidence scores are internal — never mention them unless asked.
- If the user says hi, hello, or asks a general question unrelated to sales data, respond naturally without mentioning any product data."""

FORECAST_SYSTEM_PROMPT = """You are DataToad, a sales analyst. Explain forecasts in 2-3 sentences like you're briefing a PM before a planning meeting. No bullet points. Lead with the trend direction and magnitude, then give one specific inventory or planning recommendation."""

CHITCHAT_KEYWORDS = {
    "greeting": ["hi", "hello", "hey", "howdy", "good morning", "good afternoon", "good evening"],
    "thanks":   ["thank you", "thanks", "thx", "cheers", "appreciate it", "ty"],
    "help":     ["help", "what can you do", "how do you work", "what do you know", "what can i ask"],
    "who":      ["who are you", "what are you", "what is datatoad", "what is prism", "tell me about yourself"],
}

CHITCHAT_RESPONSES = {
    "greeting": "Hey! I'm DataToad — ask me anything about your sales catalog. Try something like \"which jackets are trending up this month\" or \"forecast Pocket Jacket for the next 6 months\".",
    "thanks":   "Happy to help! Let me know if there's anything else you want to dig into.",
    "help":     "I can analyze your product catalog for trends, spikes, seasonal patterns, and volatility — and I can generate sales forecasts with confidence ranges. Try asking \"which products are trending up\" or \"forecast Pocket Jacket for 6 months\".",
    "who":      "I'm DataToad, a conversational BI assistant built on top of your Databricks catalog. I use signal processing to detect sales patterns and surface insights you'd normally spend hours finding in a dashboard.",
}


class ClaudeService:
    def __init__(self, settings: Settings):
        self.base_url = settings.nvidia_base_url.strip()
        self.api_key = settings.nvidia_api_key.strip()
        self.model = settings.nvidia_chat_model.strip()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def interpret_patterns(self, patterns_data: list[dict], user_query: str) -> str:
        # Short-circuit chitchat before hitting the API
        chitchat = self._detect_chitchat(user_query)
        if chitchat:
            return chitchat

        context = self._format_patterns_context(patterns_data)

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_message(context, user_query)}
                ],
                "temperature": 0.5,
                "max_tokens": 300,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def interpret_forecast(self, forecast_data: dict, product_info: dict) -> str:
        name = product_info.get('name', product_info.get('product_id', 'this product'))
        values = forecast_data.get('values', [])
        first = values[0] if values else 0
        last = values[-1] if values else 0
        change_pct = ((last - first) / first * 100) if first else 0
        direction = "up" if change_pct > 0 else "down"

        prompt = f"""Product: {name}
Current base sales: {product_info.get('base_sales', 'N/A')} units/week
Forecast horizon: {len(forecast_data.get('dates', []))} months
Projected change: {direction} {abs(change_pct):.0f}% ({first:.0f} → {last:.0f} units)
Peak month historically: {product_info.get('peak_month', 'N/A')}
Pattern: {product_info.get('detected_pattern', 'trending')}

Give a 2-sentence forecast briefing and one planning recommendation."""

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": FORECAST_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 200,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def stream_response(self, patterns_data: list[dict], user_query: str):
        """Stream response tokens from Nvidia NIM API"""
        # Short-circuit chitchat without streaming
        chitchat = self._detect_chitchat(user_query)
        if chitchat:
            yield chitchat
            return

        context = self._format_patterns_context(patterns_data)

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": self._build_user_message(context, user_query)}
                ],
                "temperature": 0.5,
                "max_tokens": 300,
                "stream": True
            },
            stream=True,
            timeout=120
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    line_str = line_str[6:]
                if line_str.strip() == '[DONE]':
                    break
                try:
                    import json
                    data = json.loads(line_str)
                    if data.get("choices") and len(data["choices"]) > 0:
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                except json.JSONDecodeError:
                    continue

    def _detect_chitchat(self, user_query: str) -> str | None:
        """Return a hardcoded response for greetings and off-topic queries."""
        lower = user_query.lower().strip()
        for intent, keywords in CHITCHAT_KEYWORDS.items():
            if any(lower == kw or lower.startswith(kw) for kw in keywords):
                return CHITCHAT_RESPONSES[intent]
        return None

    def _build_user_message(self, context: str, user_query: str) -> str:
        return f"PRODUCTS:\n{context}\n\nQUESTION: {user_query}"

    def _format_patterns_context(self, patterns: list[dict]) -> str:
        if not patterns:
            return "No matching products found."

        # Top 5 only sorted by base_sales
        top = sorted(patterns, key=lambda p: p.get('base_sales', 0), reverse=True)[:5]

        lines = []
        for p in top:
            name = p.get('name', p.get('product_id', 'Unknown'))
            parts = [name]

            if p.get('base_sales'):
                parts.append(f"{p['base_sales']:.0f} units/week")
            if p.get('trend_slope') is not None:
                parts.append("trending up" if p['trend_slope'] > 0 else "trending down")
            if p.get('peak_month'):
                try:
                    parts.append(f"peaks in {calendar.month_abbr[int(p['peak_month'])]}")
                except (ValueError, IndexError):
                    parts.append(f"peak month {p['peak_month']}")
            if p.get('price'):
                parts.append(f"${p['price']:.0f}")
            if p.get('detected_pattern'):
                parts.append(p['detected_pattern'])

            lines.append(" | ".join(parts))

        return "\n".join(lines)

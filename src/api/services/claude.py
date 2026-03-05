import requests
from src.config import Settings

class ClaudeService:
    def __init__(self, settings: Settings):
        self.base_url = settings.nvidia_base_url.strip()
        self.api_key = settings.nvidia_api_key.strip()
        # Use the chat completion model configured in settings
        self.model = settings.nvidia_chat_model.strip()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def interpret_patterns(self, patterns_data: list[dict], user_query: str) -> str:
        context = self._format_patterns_context(patterns_data)
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are PRISM AI, a sales pattern analysis assistant. You use mathematical transforms (STFT, wavelets, and Hilbert-Huang transform) to detect patterns in sales and combine it with product feature analysis to return relevant patterns to the user based on the query and business relevance. Be specific with numbers. Give concrete recommendations."
                    },
                    {
                        "role": "user",
                        "content": self._build_user_message(context, user_query)
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def interpret_forecast(self, forecast_data: dict, product_info: dict) -> str:
        prompt = f"""Explain this forecast in business terms.

Product: {product_info.get('name', product_info.get('product_id', 'Unknown'))}
Pattern: {product_info.get('detected_pattern', 'unknown')}
Base Sales: {product_info.get('base_sales', 'N/A')}

Forecast:
- Dates: {forecast_data['dates']}
- Predicted Values: {forecast_data['values']}
- Range: {forecast_data['lower_bound']} to {forecast_data['upper_bound']}
- Method: {forecast_data['method']}

Give 2-3 specific business recommendations based on this forecast."""

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are PRISM AI, a sales analyst. Provide actionable business insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def stream_response(self, patterns_data: list[dict], user_query: str):
        """Stream response tokens from Nvidia NIM API"""
        context = self._format_patterns_context(patterns_data)
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are PRISM AI, a sales pattern analysis assistant. You use mathematical transforms (STFT, wavelets, and Hilbert-Huang transform) to detect patterns in sales and combine it with product feature analysis to return relevant patterns to the user based on the query and business relevance. Be specific with numbers. Give concrete recommendations."
                    },
                    {
                        "role": "user",
                        "content": self._build_user_message(context, user_query)
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
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
                    line_str = line_str[6:]  # Remove 'data: ' prefix
                    
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
    
    def _build_user_message(self, context: str, user_query: str) -> str:
        return f"""PATTERN DATA:
{context}

USER QUESTION: {user_query}

Provide a helpful, specific answer with actionable business insights:"""
    
    def _format_patterns_context(self, patterns: list[dict]) -> str:
        if not patterns:
            return "No patterns found."
        
        lines = []
        for p in patterns[:15]:
            name = p.get('name', p.get('product_id', 'Unknown'))
            pattern = p.get('detected_pattern', 'unknown')
            confidence = p.get('confidence', 0)
            
            line = f"- {name}: {pattern} (confidence: {confidence:.0%})"
            
            if p.get('trend_slope'):
                direction = "↑" if p['trend_slope'] > 0 else "↓"
                line += f", trend: {direction}"
            if p.get('base_sales'):
                line += f", base sales: {p['base_sales']:.0f}"
            if p.get('volatility'):
                line += f", volatility: {p['volatility']:.2f}"
            if p.get('peak_month'):
                line += f", peak month: {p['peak_month']}"
            if p.get('price'):
                line += f", price: ${p['price']:.2f}"
            
            lines.append(line)
        
        return "\n".join(lines)
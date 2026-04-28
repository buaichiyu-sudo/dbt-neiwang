import json
from typing import Any
import requests

from core.config import Settings


class QwenClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        if self.settings.mock_mode or not self.settings.qwen_api_base:
            return self._mock_reply(user_prompt)

        payload: dict[str, Any] = {
            "model": self.settings.qwen_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        response = requests.post(
            f"{self.settings.qwen_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.qwen_api_key}"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _mock_reply(self, user_prompt: str) -> str:
        if "intent_summary" in user_prompt or "业务意图" in user_prompt:
            return json.dumps(
                {
                    "intent_summary": "统计昨日单站充电效率",
                    "metrics": ["charge_efficiency"],
                    "dimensions": ["station_id"],
                    "time_grain": "day",
                    "complexity": "Low",
                    "risk_flags": [],
                    "recommended_layer": "ADS",
                    "reasoning_brief": "常规聚合指标",
                },
                ensure_ascii=False,
            )

        return """```yaml
version: 2
models:
  - name: ads_charge_efficiency_daily
    description: 单站昨日充电效率
    metrics:
      - name: charge_efficiency
        description: 充电效率
        type: ratio
```
```sql
select station_id, dt, sum(charge_kwh)/nullif(sum(duration_hour),0) as charge_efficiency
from {{ ref('dws_charge_order_di') }}
where dt = '{{ var("biz_date") }}'
group by station_id, dt
```
"""

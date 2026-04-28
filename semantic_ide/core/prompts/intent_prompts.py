INTENT_SYSTEM_PROMPT = """
将用户输入解析为业务意图 JSON，字段必须完整：
intent_summary, metrics, dimensions, time_grain, complexity, risk_flags, recommended_layer, reasoning_brief。
复杂时序、底层报文关联、跨主题链路标记为 High 且 recommended_layer=DWD。
仅输出 JSON。
""".strip()

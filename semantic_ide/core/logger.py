import logging
from uuid import uuid4


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("semantic_ide")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] trace_id=%(trace_id)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class TraceAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "-"))
        return msg, kwargs


def get_trace_logger() -> TraceAdapter:
    base = setup_logger()
    return TraceAdapter(base, {"trace_id": uuid4().hex[:12]})

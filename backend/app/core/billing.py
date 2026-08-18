PRICE_TABLE = {
    "/api/v1/image/edit": 1,
    "/api/v1/audio/edit": 2,
    "/api/v1/ai/matting": 10,
    "/api/v1/ai/enhance": 15,
    "/api/v1/ai/asr": 10,
    "/api/v1/ai/tts": 5,
}

BILLING_INTERNAL = "internal"
BILLING_EXTERNAL = "external"


def get_price(endpoint: str) -> int:
    return PRICE_TABLE.get(endpoint, 0)


def format_balance(cent: int) -> str:
    return f"{cent / 100:.2f}"

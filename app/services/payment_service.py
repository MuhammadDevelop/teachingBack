import base64
import hashlib
import json
from app.config import get_settings


def create_payme_params(amount: int, order_id: str, return_url: str = "") -> str:
    """Create PayMe click params for redirect"""
    settings = get_settings()
    params = {
        "m": settings.payme_merchant_id,
        "ac.order_id": order_id,
        "a": amount,
        "c": return_url or settings.frontend_url + "/courses"
    }
    return base64.b64encode(json.dumps(params).encode()).decode()


def create_click_params(amount: int, order_id: str, return_url: str = "") -> str:
    """Create Click params for redirect"""
    settings = get_settings()
    params = {
        "service_id": settings.click_service_id,
        "merchant_id": settings.click_merchant_id,
        "amount": amount,
        "transaction_param": order_id,
        "return_url": return_url or settings.frontend_url + "/courses"
    }
    return base64.b64encode(json.dumps(params).encode()).decode()


def verify_payme_signature(data: dict, password: str) -> bool:
    """Verify PayMe callback signature"""
    sign = data.get("sign")
    if not sign:
        return False
    params = data.copy()
    params.pop("sign", None)
    sign_string = "".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_string += password
    calc = hashlib.md5(sign_string.encode()).hexdigest()
    return calc == sign


def verify_click_signature(data: dict) -> bool:
    """Verify Click callback signature"""
    sign = data.get("sign_string")
    if not sign:
        return False
    settings = get_settings()
    sign_string = (
        f"{data.get('click_trans_id', '')}"
        f"{data.get('service_id', '')}"
        f"{settings.click_secret_key}"
        f"{data.get('merchant_trans_id', '')}"
        f"{data.get('amount', '')}"
        f"{data.get('action', '')}"
        f"{data.get('sign_time', '')}"
    )
    calc = hashlib.md5(sign_string.encode()).hexdigest()
    return calc == sign

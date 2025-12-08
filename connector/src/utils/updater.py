import requests


def check_update(url: str) -> dict:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"update_available": False}

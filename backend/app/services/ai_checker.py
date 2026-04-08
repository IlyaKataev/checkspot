"""
AI-проверка фото через Claude.
Управляется флагом AI_MODERATION_ENABLED в .env.
В MVP отключена — все фото идут на ручную модерацию.
"""
from app.core.config import settings


async def check_photo(photo_path: str, category: str) -> dict:
    """
    Возвращает:
      {"passed": bool, "is_shelf": bool, "is_clear": bool, "has_category": bool, "reason": str}
    """
    if not settings.AI_MODERATION_ENABLED:
        return {"passed": None, "reason": "manual_review"}

    import anthropic
    import base64

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    with open(photo_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    prompt = (
        f"You are a retail shelf auditor. Analyze this photo and answer in JSON:\n"
        f"1. is_shelf: Is this a photo of a retail store shelf?\n"
        f"2. is_clear: Is the photo clear (not blurry, good lighting)?\n"
        f"3. has_category: Does the shelf contain products from category '{category}'?\n"
        f"4. reason: Brief explanation if any check failed (in Russian), else empty string.\n"
        f"Respond ONLY with JSON: {{\"is_shelf\": bool, \"is_clear\": bool, \"has_category\": bool, \"reason\": string}}"
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                {"type": "text", "text": prompt},
            ],
        }],
    )

    import json
    text = response.content[0].text.strip()
    result = json.loads(text)
    result["passed"] = result["is_shelf"] and result["is_clear"] and result["has_category"]
    return result

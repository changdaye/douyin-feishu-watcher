from app.models import VideoRecord
from app.notifier import build_card_payload, build_text_payload, enrich_payload_with_signature


def test_build_card_payload_contains_core_fields():
    video = VideoRecord(
        creator_name="Alice",
        video_id="vid-1",
        title="Hello",
        video_url="https://example.com/v/1",
    )

    payload = build_card_payload(video)

    assert payload["msg_type"] == "interactive"
    assert "Alice" in str(payload)
    assert "https://example.com/v/1" in str(payload)


def test_build_text_payload_is_plaintext_fallback():
    video = VideoRecord(
        creator_name="Alice",
        video_id="vid-1",
        title="Hello",
        video_url="https://example.com/v/1",
    )

    payload = build_text_payload(video)

    assert payload["msg_type"] == "text"
    assert "Hello" in payload["content"]["text"]


def test_enrich_payload_with_signature_adds_timestamp_and_sign():
    payload = {"msg_type": "text", "content": {"text": "hello"}}

    enriched = enrich_payload_with_signature(payload, secret="test-secret", timestamp=1700000000)

    assert enriched["timestamp"] == "1700000000"
    assert enriched["sign"]
    assert enriched["msg_type"] == "text"
    assert enriched["content"]["text"] == "hello"

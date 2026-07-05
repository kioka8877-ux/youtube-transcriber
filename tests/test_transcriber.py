"""
Tests unitaires — YouTube Transcriber
Tests des validators, frégates et forge.
"""

import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.validators import validate_url, detect_url_type, validate_youtube_url, validate_tiktok_url
from frigates import FORGE


# === Tests validators ===

def test_validate_youtube_video():
    result = validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result["valid"] is True
    assert result["platform"] == "youtube"
    assert result["type"] == "youtube_video"
    print("✅ test_validate_youtube_video")


def test_validate_youtube_short():
    result = validate_url("https://youtu.be/dQw4w9WgXcQ")
    assert result["valid"] is True
    assert result["platform"] == "youtube"
    assert result["type"] == "youtube_video"
    print("✅ test_validate_youtube_short")


def test_validate_youtube_channel():
    result = validate_url("https://youtube.com/@SomeChannel")
    assert result["valid"] is True
    assert result["platform"] == "youtube"
    assert result["type"] == "youtube_channel"
    print("✅ test_validate_youtube_channel")


def test_validate_youtube_playlist():
    result = validate_url("https://youtube.com/playlist?list=PLrAXtmRdnEQy6nuudfH7")
    assert result["valid"] is True
    assert result["platform"] == "youtube"
    assert result["type"] == "youtube_playlist"
    print("✅ test_validate_youtube_playlist")


def test_validate_tiktok_video():
    result = validate_url("https://www.tiktok.com/@user/video/1234567890")
    assert result["valid"] is True
    assert result["platform"] == "tiktok"
    assert result["type"] == "tiktok_video"
    print("✅ test_validate_tiktok_video")


def test_validate_tiktok_profile():
    result = validate_url("https://www.tiktok.com/@user")
    assert result["valid"] is True
    assert result["platform"] == "tiktok"
    assert result["type"] == "tiktok_profile"
    print("✅ test_validate_tiktok_profile")


def test_validate_invalid_url():
    result = validate_url("https://example.com/random")
    assert result["valid"] is False
    assert result["type"] == "unknown"
    print("✅ test_validate_invalid_url")


def test_validate_empty_url():
    result = validate_url("")
    assert result["valid"] is False
    assert "vide" in result["error"]
    print("✅ test_validate_empty_url")


# === Tests FORGE ===

def test_forge_json():
    results = [{
        "video_id": "test123",
        "title": "Test Video",
        "url": "https://youtube.com/watch?v=test123",
        "status": "OK",
        "transcript": [
            {"start": 0.0, "text": "Bonjour", "duration": 2.0},
            {"start": 2.0, "text": "Monde", "duration": 1.5},
        ],
    }]
    out = FORGE.run(results, "json")
    assert out["format"] == "json"
    assert out["filename"] == "transcripts.json"
    assert "Bonjour" in out["content"]
    assert "test123" in out["content"]
    print("✅ test_forge_json")


def test_forge_srt():
    results = [{
        "video_id": "test123",
        "title": "Test Video",
        "url": "https://youtube.com/watch?v=test123",
        "status": "OK",
        "transcript": [
            {"start": 0.0, "text": "Bonjour", "duration": 2.0},
            {"start": 2.0, "text": "Monde", "duration": 1.5},
        ],
    }]
    out = FORGE.run(results, "srt")
    assert out["format"] == "srt"
    assert "00:00:00,000 --> 00:00:02,000" in out["content"]
    assert "Bonjour" in out["content"]
    print("✅ test_forge_srt")


def test_forge_txt():
    results = [{
        "video_id": "test123",
        "title": "Test Video",
        "url": "https://youtube.com/watch?v=test123",
        "status": "OK",
        "transcript": [
            {"start": 0.0, "text": "Bonjour", "duration": 2.0},
            {"start": 2.0, "text": "Monde", "duration": 1.5},
        ],
    }]
    out = FORGE.run(results, "txt")
    assert out["format"] == "txt"
    assert "=== Test Video ===" in out["content"]
    assert "Bonjour" in out["content"]
    print("✅ test_forge_txt")


def test_forge_skips_failed():
    results = [
        {"video_id": "fail", "title": "Failed", "url": "", "status": "ECHEC", "transcript": []},
        {"video_id": "ok", "title": "OK", "url": "https://youtube.com/watch?v=ok", "status": "OK", "transcript": [{"start": 0, "text": "Hello", "duration": 1}]},
    ]
    out = FORGE.run(results, "json")
    assert "fail" not in out["content"]
    assert "ok" in out["content"]
    print("✅ test_forge_skips_failed")


def test_forge_invalid_format():
    try:
        FORGE.run([], "xml")
        assert False, "Should have raised"
    except ValueError as e:
        assert "xml" in str(e)
        print("✅ test_forge_invalid_format")


# === Runner ===

def run_all():
    tests = [
        test_validate_youtube_video,
        test_validate_youtube_short,
        test_validate_youtube_channel,
        test_validate_youtube_playlist,
        test_validate_tiktok_video,
        test_validate_tiktok_profile,
        test_validate_invalid_url,
        test_validate_empty_url,
        test_forge_json,
        test_forge_srt,
        test_forge_txt,
        test_forge_skips_failed,
        test_forge_invalid_format,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"❌ {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Résultat: {passed} passés, {failed} échoués, {passed + failed} total")


if __name__ == "__main__":
    run_all()

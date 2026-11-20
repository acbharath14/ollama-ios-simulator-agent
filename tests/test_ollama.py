import base64
import json

import pytest

from simagent import ollama


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_chat_payload_shape():
    payload = ollama.chat_payload(
        "qwen2.5-coder:7b",
        [{"role": "user", "content": "hi"}],
        temperature=0.1,
    )
    assert payload["model"] == "qwen2.5-coder:7b"
    assert payload["messages"][0]["content"] == "hi"
    assert payload["temperature"] == 0.1
    assert payload["stream"] is False


def test_describe_payload_embeds_image(tmp_path):
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"\x89PNG fake image bytes")
    payload = ollama.describe_payload("qwen2.5vl:7b", str(shot), "What is on screen?")
    message = payload["messages"][0]
    assert message["content"] == "What is on screen?"
    assert message["images"] == [base64.b64encode(b"\x89PNG fake image bytes").decode("ascii")]
    assert payload["temperature"] == 0.1


def test_describe_payload_missing_file(tmp_path):
    with pytest.raises(OSError):
        ollama.describe_payload("qwen2.5vl:7b", str(tmp_path / "nope.png"), "What?")


def test_fix_prompt_contents():
    prompt = ollama.fix_prompt("App.swift", "let x = 1", "button does nothing")
    assert "App.swift" in prompt
    assert "button does nothing" in prompt
    assert "let x = 1" in prompt
    assert "git apply" in prompt


def test_chat_success(monkeypatch):
    def fake_urlopen(req, timeout=None):
        assert req.full_url == "http://127.0.0.1:11434/api/chat"
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "qwen2.5-coder:7b"
        return FakeResponse({"message": {"content": "hello from the model"}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = ollama.chat(
        "http://127.0.0.1:11434",
        "qwen2.5-coder:7b",
        [{"role": "user", "content": "hi"}],
    )
    assert out == "hello from the model"


def test_chat_unreachable(monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(ollama.OllamaError, match="cannot reach Ollama"):
        ollama.chat("http://127.0.0.1:11434", "qwen2.5-coder:7b", [])


def test_chat_unexpected_shape(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return FakeResponse({"nope": True})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    with pytest.raises(ollama.OllamaError, match="unexpected Ollama response"):
        ollama.chat("http://127.0.0.1:11434", "qwen2.5-coder:7b", [])


def test_reachable_false(monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert ollama.reachable("http://127.0.0.1:11434") is False


def test_reachable_true(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return FakeResponse({"models": []})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert ollama.reachable("http://127.0.0.1:11434") is True

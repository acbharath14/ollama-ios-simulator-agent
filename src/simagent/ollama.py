"""Ollama client over stdlib urllib only. No third-party HTTP library.

The client never invents a model response. A failed call raises OllamaError
and the caller reports the step as failed.
"""

import base64
import json
import urllib.error
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_VISION_MODEL = "qwen2.5vl:7b"
DEFAULT_CODER_MODEL = "qwen2.5-coder:7b"


class OllamaError(Exception):
    pass


def chat_payload(model, messages, temperature=0.1, stream=False):
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }


def describe_payload(model, image_path, question):
    """One screenshot plus one narrow question, as a single chat message."""
    with open(image_path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": question,
                "images": [encoded],
            }
        ],
        "temperature": 0.1,
        "stream": False,
    }


def fix_prompt(file_path, file_text, problem):
    """Short prompt for one single-file fix. The model answers with the full corrected file."""
    return (
        "You are fixing one problem in one file. Reply with the full corrected "
        "file contents only, in a fenced code block. No explanation and no prose "
        "outside the code block. Change only what the problem requires; keep "
        "every other line exactly as it is.\n"
        "File: %s\n"
        "Problem: %s\n"
        "Current file contents:\n%s\n"
        % (file_path, problem, file_text)
    )


def chat(host, model, messages, temperature=0.1, timeout=600):
    return _post(host, chat_payload(model, messages, temperature), timeout)


def describe_image(host, model, image_path, question, timeout=600):
    return _post(host, describe_payload(model, image_path, question), timeout)


def _post(host, payload, timeout):
    url = host.rstrip("/") + "/api/chat"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise OllamaError("cannot reach Ollama at %s: %s" % (host, exc)) from exc
    except ValueError as exc:
        raise OllamaError("bad response from Ollama at %s: %s" % (host, exc)) from exc
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaError("unexpected Ollama response shape: %r" % (data,)) from exc


def reachable(host, timeout=5):
    """Probe only. True when the Ollama server answers, False otherwise."""
    try:
        req = urllib.request.Request(host.rstrip("/") + "/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

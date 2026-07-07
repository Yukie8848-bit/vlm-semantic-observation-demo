from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


def image_to_data_url(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


class VLMClient:
    def __init__(self) -> None:
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        self.api_style = os.getenv("VLM_API_STYLE", "openai").lower()
        self.api_key = os.getenv("API_KEY", "")
        self.base_url = os.getenv("BASE_URL")
        self.model = os.getenv("MODEL_NAME", "")
        self.endpoint = os.getenv("VLM_ENDPOINT", "")
        self.timeout = int(os.getenv("REQUEST_TIMEOUT", "60"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))

        if not self.model:
            raise ValueError("MODEL_NAME is required. Copy .env.example to .env and configure it.")

    def analyze_image(self, image_path: Path, system_prompt: str, user_prompt: str) -> str:
        data_url = image_to_data_url(image_path)
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.api_style == "requests":
                    return self._call_requests_api(data_url, system_prompt, user_prompt)
                return self._call_openai_api(data_url, system_prompt, user_prompt)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))

        raise RuntimeError(f"VLM request failed after {self.max_retries} attempts: {last_error}")

    def _call_openai_api(self, data_url: str, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
            timeout=self.timeout,
        )
        return response.choices[0].message.content or ""

    def _call_requests_api(self, data_url: str, system_prompt: str, user_prompt: str) -> str:
        if not self.endpoint:
            raise ValueError("VLM_ENDPOINT is required when VLM_API_STYLE=requests.")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "image": data_url,
            "temperature": 0,
        }
        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict):
            if "text" in data:
                return str(data["text"])
            if "content" in data:
                return str(data["content"])
            choices = data.get("choices")
            if choices:
                message = choices[0].get("message", {})
                return str(message.get("content", ""))
        return str(data)

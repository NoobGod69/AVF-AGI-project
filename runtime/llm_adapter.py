# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)


class LLMAdapter:
    def __init__(self, model_name: str = "gpt2", max_new_tokens: int = 64) -> None:
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self._pipeline = None

    def _load_pipeline(self) -> None:
        if self._pipeline is None:
            from transformers import pipeline  # type: ignore

            self._pipeline = pipeline("text-generation", model=self.model_name)

    def summarize_context(self, context: Dict) -> str:
        raw = str(context)
        return raw[:1000]

    def generate(self, context: Dict, user_input: str) -> str:
        prompt = f"Context: {self.summarize_context(context)}\nUser: {user_input}\nAssistant:"
        try:
            self._load_pipeline()
            output = self._pipeline(
                prompt,
                max_new_tokens=self.max_new_tokens,
                pad_token_id=0,
            )
            return output[0]["generated_text"].replace(prompt, "").strip()
        except Exception as exc:
            LOGGER.exception("LLM generation failed: %s", exc)
            return "[LLM unavailable]"


class MockLLM:
    def __init__(self, prefix: str = "mock") -> None:
        self.prefix = prefix

    def summarize_context(self, context: Dict) -> str:
        return str(context)

    def generate(self, context: Dict, user_input: str) -> str:
        return f"{self.prefix}: {user_input}"

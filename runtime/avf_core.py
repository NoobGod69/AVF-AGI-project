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
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from runtime.avf_io import AVFAppendWriter, AVFStreamReader
from runtime.snapshot import SnapshotController as _SnapshotController, write_snapshot

LOGGER = logging.getLogger(__name__)


@dataclass
class PersistentIdentity:
    identifier: str
    personality: Dict[str, str] = field(default_factory=dict)


class SnapshotController(_SnapshotController):
    pass


@dataclass
class CognitiveCore:
    state: Dict[str, List[Dict]] = field(default_factory=lambda: {"events": []})
    identity: Optional[PersistentIdentity] = None
    snapshot_controller: SnapshotController = field(default_factory=SnapshotController)

    def apply_event(self, ev: Dict) -> None:
        self.state.setdefault("events", []).append(ev)
        if ev.get("type") == "identity":
            self.identity = PersistentIdentity(ev["identifier"], ev.get("personality", {}))

    def reconstruct_from_avf(self, path: str) -> None:
        reader = AVFStreamReader(path)
        self.state = {"events": []}
        for chunk in reader.stream():
            ctype = chunk["type"]
            payload = chunk["payload"]
            if ctype == "SNAPSHOT":
                self.state = payload
                continue
            if ctype == "IDENTITY":
                self.identity = PersistentIdentity(
                    payload["identifier"], payload.get("personality", {})
                )
                continue
            if ctype == "EVENT":
                self.apply_event(payload)

    def think_with_llm(
        self,
        llm_adapter,
        writer: AVFAppendWriter,
        user_input: str,
    ) -> str:
        context = {
            "identity": self.identity.identifier if self.identity else "anonymous",
            "recent_events": self.state.get("events", [])[-5:],
        }
        response = llm_adapter.generate(context, user_input)
        event = {"type": "llm_response", "input": user_input, "output": response}
        writer.append_chunk("EVENT", event)
        self.apply_event(event)
        self.snapshot_controller.tick()
        if self.snapshot_controller.should_snapshot():
            write_snapshot(writer, self.state)
            self.snapshot_controller.reset()
        return response

    def persist_identity(self, writer: AVFAppendWriter) -> None:
        if not self.identity:
            raise ValueError("Identity not set")
        writer.append_chunk(
            "IDENTITY",
            {
                "identifier": self.identity.identifier,
                "personality": self.identity.personality,
            },
        )

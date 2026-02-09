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
from dataclasses import dataclass
from typing import Dict, List, Optional

from runtime.avf_io import AVFAppendWriter, AVFStreamReader

LOGGER = logging.getLogger(__name__)


@dataclass
class SnapshotController:
    interval: int = 100
    counter: int = 0

    def should_snapshot(self) -> bool:
        return self.counter >= self.interval

    def tick(self) -> None:
        self.counter += 1

    def reset(self) -> None:
        self.counter = 0

    def manual_snapshot(self) -> None:
        self.counter = self.interval


def write_snapshot(writer: AVFAppendWriter, state: Dict) -> None:
    writer.append_chunk("SNAPSHOT", state)


def replay_with_snapshot(avf_path: str):
    from runtime.avf_core import CognitiveCore, PersistentIdentity

    reader = AVFStreamReader(avf_path)
    last_snapshot: Optional[Dict] = None
    post_snapshot_events: List[Dict] = []
    identity_payload: Optional[Dict] = None
    for chunk in reader.stream():
        ctype = chunk["type"]
        payload = chunk["payload"]
        if ctype == "SNAPSHOT":
            last_snapshot = payload
            post_snapshot_events = []
            continue
        if ctype == "IDENTITY":
            identity_payload = payload
        if ctype == "EVENT":
            post_snapshot_events.append(payload)

    core = CognitiveCore()
    if last_snapshot is not None:
        core.state = last_snapshot
    if identity_payload is not None:
        core.identity = PersistentIdentity(
            identity_payload["identifier"],
            identity_payload.get("personality", {}),
        )
    for ev in post_snapshot_events:
        core.apply_event(ev)
    return core

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

import json
import os
from pathlib import Path

from runtime.avf_core import CognitiveCore, PersistentIdentity
from runtime.avf_io import AVFAppendWriter
from runtime.snapshot import write_snapshot


def main() -> None:
    base_path = Path("/content" if os.path.exists("/content") else "/mnt/data")
    base_path.mkdir(parents=True, exist_ok=True)
    avf_path = base_path / "sample.avf"

    writer = AVFAppendWriter(str(avf_path))
    core = CognitiveCore()
    core.identity = PersistentIdentity("avf-demo", {"tone": "curious"})
    core.persist_identity(writer)

    for idx in range(100):
        writer.append_chunk("EVENT", {"type": "concept", "value": f"c{idx}"})
        if idx > 0 and idx % 50 == 0:
            write_snapshot(writer, core.state)

    report = {"path": str(avf_path), "events": 100}
    (base_path / "sample_report.json").write_text(json.dumps(report, indent=2))
    print(f"Sample AVF written to {avf_path}")


if __name__ == "__main__":
    main()

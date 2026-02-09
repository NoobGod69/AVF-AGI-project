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

import os
import shutil
import tempfile

from runtime.avf_io import AVFAppendWriter, AVFStreamReader, build_chunk_bytes, scan_avf_with_end
from runtime.snapshot import write_snapshot


def test_write_scan_read() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sample.avf")
        writer = AVFAppendWriter(path)
        for idx in range(200):
            writer.append_chunk("EVENT", {"type": "concept", "value": f"v{idx}"})
            if idx in {99, 199}:
                write_snapshot(writer, {"events": ["snapshot", idx]})
        reader = AVFStreamReader(path)
        chunks = list(reader.stream())
        assert len(chunks) >= 202
        scan = scan_avf_with_end(path)
        assert scan["last_good_end"] == os.path.getsize(path)


def test_truncate_recover() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "truncate.avf")
        writer = AVFAppendWriter(path)
        for idx in range(10):
            writer.append_chunk("EVENT", {"type": "concept", "value": f"v{idx}"})
        backup = path + ".bak"
        shutil.copy(path, backup)
        with open(path, "r+b") as handle:
            handle.seek(-1, os.SEEK_END)
            last = handle.read(1)
            handle.seek(-1, os.SEEK_END)
            handle.write(bytes([last[0] ^ 0xFF]))
        scan = scan_avf_with_end(path)
        assert scan["last_good_end"] is not None
        with open(path, "rb+") as handle:
            handle.truncate(scan["last_good_end"])
        chunks = list(AVFStreamReader(path).stream())
        assert chunks
        assert os.path.getsize(path) <= os.path.getsize(backup)


def test_atomic_append_no_partial() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "atomic.avf")
        chunk = build_chunk_bytes("EVENT", {"type": "concept", "value": "ok"})
        writer = AVFAppendWriter(path)
        writer.append_chunk("EVENT", {"type": "concept", "value": "ok"})
        with open(path, "ab") as handle:
            handle.write(chunk[:10])
        scan = scan_avf_with_end(path)
        assert scan["last_good_end"] == os.path.getsize(path) - 10

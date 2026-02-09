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
import logging
import os
import struct
import time
import zlib
from dataclasses import dataclass
from hashlib import sha256
from typing import Dict, Iterable, List, Optional

LOGGER = logging.getLogger(__name__)

MAGIC = b"AVF1"
HEADER_STRUCT = struct.Struct(">4s16sQI")
CHECKSUM_SIZE = 32


@dataclass
class AVFChunkInfo:
    ctype: str
    timestamp: int
    start: int
    end: int
    size: int


def _normalize_type(ctype: str) -> bytes:
    raw = ctype.encode("utf-8")[:16]
    return raw.ljust(16, b"\x00")


def build_chunk_bytes(ctype: str, payload: Dict) -> bytes:
    """Build a chunk with compressed payload and checksum."""
    encoded = json.dumps(payload).encode("utf-8")
    compressed = zlib.compress(encoded)
    timestamp = int(time.time() * 1000)
    header = HEADER_STRUCT.pack(MAGIC, _normalize_type(ctype), timestamp, len(compressed))
    checksum = sha256(header + compressed).digest()
    return header + compressed + checksum


def atomic_append(path: str, chunk_bytes: bytes) -> None:
    """Append bytes with a single write + fsync.

    Limitation: without fcntl (e.g., on Windows), advisory file locking
    is unavailable and concurrent writers are not coordinated.
    """
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    fd = os.open(path, flags, 0o644)
    try:
        try:
            import fcntl  # type: ignore

            fcntl.flock(fd, fcntl.LOCK_EX)
        except Exception as exc:  # pragma: no cover - platform dependent
            LOGGER.warning("fcntl lock unavailable: %s", exc)
        total = 0
        while total < len(chunk_bytes):
            written = os.write(fd, chunk_bytes[total:])
            if written == 0:
                raise OSError("Failed to write chunk bytes")
            total += written
        os.fsync(fd)
    finally:
        try:
            os.close(fd)
        except OSError:
            LOGGER.exception("Failed to close file descriptor")


class AVFAppendWriter:
    def __init__(self, path: str) -> None:
        self.path = path

    def append_chunk(self, ctype: str, payload: Dict) -> None:
        chunk_bytes = build_chunk_bytes(ctype, payload)
        atomic_append(self.path, chunk_bytes)


class AVFStreamReader:
    def __init__(self, path: str) -> None:
        self.path = path

    def stream(self) -> Iterable[Dict]:
        with open(self.path, "rb") as handle:
            while True:
                start = handle.tell()
                header_bytes = handle.read(HEADER_STRUCT.size)
                if not header_bytes:
                    break
                if len(header_bytes) < HEADER_STRUCT.size:
                    LOGGER.warning("Incomplete header at %s", start)
                    break
                magic, ctype_raw, timestamp, size = HEADER_STRUCT.unpack(header_bytes)
                if magic != MAGIC:
                    raise ValueError(f"Invalid magic at {start}")
                payload_bytes = handle.read(size)
                checksum = handle.read(CHECKSUM_SIZE)
                if len(payload_bytes) < size or len(checksum) < CHECKSUM_SIZE:
                    LOGGER.warning("Incomplete chunk at %s", start)
                    break
                expected = sha256(header_bytes + payload_bytes).digest()
                if expected != checksum:
                    raise ValueError(f"Checksum mismatch at {start}")
                decompressed = zlib.decompress(payload_bytes)
                payload = json.loads(decompressed.decode("utf-8"))
                yield {
                    "type": ctype_raw.rstrip(b"\x00").decode("utf-8"),
                    "timestamp": timestamp,
                    "payload": payload,
                }


def scan_avf_with_end(path: str) -> Dict[str, Optional[List[AVFChunkInfo]]]:
    chunks: List[AVFChunkInfo] = []
    last_good_end: Optional[int] = 0
    if not os.path.exists(path):
        return {"chunks": chunks, "last_good_end": None}
    with open(path, "rb") as handle:
        while True:
            start = handle.tell()
            header_bytes = handle.read(HEADER_STRUCT.size)
            if not header_bytes:
                break
            if len(header_bytes) < HEADER_STRUCT.size:
                break
            try:
                magic, ctype_raw, timestamp, size = HEADER_STRUCT.unpack(header_bytes)
            except struct.error:
                break
            if magic != MAGIC:
                break
            payload_bytes = handle.read(size)
            checksum = handle.read(CHECKSUM_SIZE)
            if len(payload_bytes) < size or len(checksum) < CHECKSUM_SIZE:
                break
            expected = sha256(header_bytes + payload_bytes).digest()
            if expected != checksum:
                break
            end = handle.tell()
            chunks.append(
                AVFChunkInfo(
                    ctype=ctype_raw.rstrip(b"\x00").decode("utf-8"),
                    timestamp=timestamp,
                    start=start,
                    end=end,
                    size=size,
                )
            )
            last_good_end = end
    return {"chunks": chunks, "last_good_end": last_good_end}

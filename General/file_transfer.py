"""
file_transfer.py — Dateiübertragungs-Protokoll über WebRTC DataChannels

Protokoll:
  1. Text-Kontrollnachricht (Präfix \x02):
       \x02{"type":"file_meta","id":"a1b2c3d4","name":"foto.jpg","size":204800}
  2. Binäre Chunks:
       [8 Byte File-ID als ASCII] + [Chunk-Daten]
  3. Text-Abschluss:
       \x02{"type":"file_end","id":"a1b2c3d4"}
"""

import json
import uuid

# ── Protokoll-Konstanten ─────────────────────────────────────
CTRL_PREFIX = "\x02"   # Präfix für Kontrollnachrichten (STX)
FILE_ID_LEN = 8        # Länge der File-ID (Bytes / ASCII-Zeichen)
CHUNK_SIZE  = 65536    # 64 KB pro Chunk


# ════════════════════════════════════════════════════════════
# Protokoll-Hilfsfunktionen (stateless, rein funktional)
# ════════════════════════════════════════════════════════════

def generate_id() -> str:
    """Erzeugt eine eindeutige 8-stellige File-ID."""
    return uuid.uuid4().hex[:FILE_ID_LEN]


def encode_meta(file_id: str, name: str, size: int) -> str:
    """Erzeugt die Metadaten-Kontrollnachricht (Text)."""
    payload = json.dumps({"type": "file_meta", "id": file_id, "name": name, "size": size})
    return CTRL_PREFIX + payload


def encode_end(file_id: str) -> str:
    """Erzeugt die Abschluss-Kontrollnachricht (Text)."""
    payload = json.dumps({"type": "file_end", "id": file_id})
    return CTRL_PREFIX + payload


def encode_chunk(file_id: str, data: bytes) -> bytes:
    """Verpackt einen Daten-Chunk mit File-ID-Präfix."""
    return file_id.encode("ascii") + data


def is_control(msg) -> bool:
    """Prüft ob eine Nachricht eine Kontrollnachricht ist."""
    return isinstance(msg, str) and msg.startswith(CTRL_PREFIX)


def is_chunk(msg) -> bool:
    """Prüft ob eine Nachricht ein binärer Datei-Chunk ist."""
    return isinstance(msg, bytes) and len(msg) >= FILE_ID_LEN


def is_chat(msg) -> bool:
    """Prüft ob eine Nachricht eine normale Chat-Nachricht ist."""
    return isinstance(msg, str) and not msg.startswith(CTRL_PREFIX)


def parse_control(msg: str) -> dict:
    """Parst eine Kontrollnachricht zu einem Dict."""
    return json.loads(msg[len(CTRL_PREFIX):])


def parse_chunk(msg: bytes) -> tuple[str, bytes]:
    """Trennt File-ID und Chunk-Daten aus einer binären Nachricht."""
    file_id = msg[:FILE_ID_LEN].decode("ascii")
    data    = msg[FILE_ID_LEN:]
    return file_id, data


def format_size(size: int) -> str:
    """Formatiert eine Byte-Anzahl menschenlesbar (z.B. '2.3 MB')."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ════════════════════════════════════════════════════════════
# FileReceiver — sammelt eingehende Chunks zu vollständigen Dateien
# ════════════════════════════════════════════════════════════

class FileReceiver:
    """
    Zustandsbehafteter Empfänger für Dateiübertragungen.
    Kann mehrere gleichzeitige Übertragungen verwalten.
    """

    def __init__(self) -> None:
        self._pending: dict[str, dict] = {}

    def on_meta(self, data: dict) -> None:
        """Registriert eine neue erwartete Datei."""
        self._pending[data["id"]] = {
            "name":   data["name"],
            "size":   data["size"],
            "chunks": [],
        }

    def on_chunk(self, file_id: str, chunk: bytes) -> None:
        """Fügt einen empfangenen Chunk zur Sammlung hinzu."""
        if file_id in self._pending:
            self._pending[file_id]["chunks"].append(chunk)

    def on_end(self, file_id: str) -> tuple[str, int, bytes] | None:
        """
        Schließt eine Übertragung ab.
        Gibt (name, size, data) zurück wenn vollständig, sonst None.
        """
        if file_id not in self._pending:
            return None
        entry = self._pending.pop(file_id)
        data  = b"".join(entry["chunks"])
        return entry["name"], entry["size"], data

    def has_pending(self, file_id: str) -> bool:
        return file_id in self._pending

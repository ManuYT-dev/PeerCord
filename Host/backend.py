"""
backend.py — Gesamte Backend-Logik
  - AsyncBridge: asyncio-Loop im Hintergrundthread
  - Kommuniziert mit der UI ausschließlich über Qt-Signals
  - Unterstützt Chat-Nachrichten UND Dateiübertragungen
"""

import asyncio
import json
import os
import threading
import pyperclip

from PyQt6.QtCore import QObject, pyqtSignal
from aiortc import RTCPeerConnection, RTCSessionDescription

from General.constants import STUN_SERVER
from General import file_transfer as ft


class AsyncBridge(QObject):
    """
    Führt den asyncio-Event-Loop in einem Daemon-Thread aus.
    Alle Ergebnisse werden als Qt-Signals an die UI gemeldet.
    """

    # ── Signals ──────────────────────────────────────────────
    sig_log           = pyqtSignal(str, str)         # (sender, nachricht)
    sig_user_join     = pyqtSignal(int)              # Clients nach Join
    sig_user_leave    = pyqtSignal(int)              # Clients nach Leave
    sig_answer        = pyqtSignal()                 # Answer fertig → Button freischalten
    sig_error         = pyqtSignal(str)              # Fehlermeldung
    sig_file_received = pyqtSignal(str, str, int, bytes)  # (sender, name, size, data)

    def __init__(self) -> None:
        super().__init__()
        self.active_channels: list = []
        self._receiver = ft.FileReceiver()
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    # ── Öffentliche Methoden ─────────────────────────────────

    def submit(self, coro) -> None:
        """Reicht eine Coroutine sicher an den Hintergrund-Loop weiter."""
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def broadcast(self, message, exclude=None) -> None:
        """Sendet Text oder Bytes an alle offenen Kanäle."""
        for ch in self.active_channels:
            if ch != exclude and ch.readyState == "open":
                ch.send(message)

    def send_host_message(self, msg: str) -> None:
        self.broadcast(f"[Host]: {msg}")

    # ── WebRTC-Verbindungsaufbau ─────────────────────────────

    async def setup_connection(self, offer_dict: dict) -> None:
        """Nimmt ein Client-Offer entgegen und erstellt eine Answer."""
        try:
            pc = RTCPeerConnection(configuration=STUN_SERVER)
            self._register_datachannel_events(pc)

            await pc.setRemoteDescription(
                RTCSessionDescription(sdp=offer_dict["sdp"], type=offer_dict["type"])
            )
            await pc.setLocalDescription(await pc.createAnswer())
            await asyncio.sleep(2)

            answer_str = json.dumps({
                "sdp":  pc.localDescription.sdp,
                "type": pc.localDescription.type,
            })
            pyperclip.copy(answer_str)
            self.sig_log.emit("SYSTEM", "✅ Answer kopiert — gib sie dem Client.")

        except Exception as exc:
            self.sig_error.emit(str(exc))
        finally:
            self.sig_answer.emit()

    # ── Datei senden ─────────────────────────────────────────

    async def send_file(self, filepath: str) -> None:
        """
        Liest eine Datei und überträgt sie in Chunks an alle Clients.
        Zeigt die Datei auch lokal in der HOST-UI an.
        """
        try:
            name = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                file_data = f.read()
            size    = len(file_data)
            file_id = ft.generate_id()

            # Lokal in der Host-UI anzeigen
            self.sig_file_received.emit("HOST", name, size, file_data)

            if not self.active_channels:
                self.sig_log.emit("SYSTEM", "Keine Clients verbunden — Datei nur lokal angezeigt.")
                return

            # Metadaten senden
            self.broadcast(ft.encode_meta(file_id, name, size))
            await asyncio.sleep(0)

            # Daten in Chunks senden
            for offset in range(0, size, ft.CHUNK_SIZE):
                chunk = file_data[offset : offset + ft.CHUNK_SIZE]
                self.broadcast(ft.encode_chunk(file_id, chunk))
                await asyncio.sleep(0)

            # Abschluss signalisieren
            self.broadcast(ft.encode_end(file_id))
            self.sig_log.emit("SYSTEM", f"Datei '{name}' gesendet ({ft.format_size(size)}).")

        except Exception as exc:
            self.sig_error.emit(f"Fehler beim Senden: {exc}")

    # ── Private Hilfsmethoden ────────────────────────────────

    def _register_datachannel_events(self, pc: RTCPeerConnection) -> None:
        @pc.on("datachannel")
        def on_datachannel(channel):
            self._on_client_connect(channel)

    def _on_client_connect(self, channel) -> None:
        self.active_channels.append(channel)
        count = len(self.active_channels)
        self.sig_user_join.emit(count)
        self.sig_log.emit("SYSTEM", f"★ Neuer User verbunden! (Gesamt: {count})")
        self.broadcast("─── Ein neuer User ist beigetreten ───", exclude=channel)

        @channel.on("message")
        def on_message(msg):
            self._route_message(msg, channel)

        @channel.on("close")
        def on_close():
            self._on_client_disconnect(channel)

    def _on_client_disconnect(self, channel) -> None:
        if channel in self.active_channels:
            self.active_channels.remove(channel)
        count = len(self.active_channels)
        self.sig_user_leave.emit(count)
        self.sig_log.emit("SYSTEM", "Ein User hat den Chat verlassen.")
        self.broadcast("─── Ein User hat den Chat verlassen ───")

    def _route_message(self, msg, sender_channel) -> None:
        """
        Verteilt eingehende Nachrichten nach Typ:
          - Kontrollnachricht → Datei-Protokoll-Handler
          - Binärdaten        → Chunk-Sammler
          - Text              → Chat-Log + Broadcast
        """
        if ft.is_control(msg):
            self._handle_control(msg, sender_channel)

        elif ft.is_chunk(msg):
            file_id, chunk = ft.parse_chunk(msg)
            self._receiver.on_chunk(file_id, chunk)
            self.broadcast(msg, exclude=sender_channel)   # an andere Clients weiterleiten

        elif ft.is_chat(msg):
            clean = msg.replace("[Host]: ", "").replace("[User]: ", "")
            self.sig_log.emit("USER", clean)
            self.broadcast(f"[User]: {clean}", exclude=sender_channel)

    def _handle_control(self, msg: str, sender_channel) -> None:
        """Verarbeitet Datei-Metadaten und Abschluss-Signale."""
        try:
            data = ft.parse_control(msg)
        except Exception:
            return

        ctrl_type = data.get("type")

        if ctrl_type == "file_meta":
            self._receiver.on_meta(data)
            self.broadcast(msg, exclude=sender_channel)

        elif ctrl_type == "file_end":
            result = self._receiver.on_end(data.get("id", ""))
            if result:
                name, size, file_data = result
                self.sig_file_received.emit("USER", name, size, file_data)
                self.sig_log.emit("SYSTEM", f"Datei '{name}' empfangen ({ft.format_size(size)}).")
            self.broadcast(msg, exclude=sender_channel)

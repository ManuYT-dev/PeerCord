import asyncio
import json
import os
import threading
import pyperclip

from PyQt6.QtCore import QObject, pyqtSignal
from aiortc import RTCPeerConnection, RTCSessionDescription

from General.constants import STUN_SERVER
import General.file_transfer as ft


class AsyncBridge(QObject):
    """Führt den asyncio-Event-Loop für den Client aus."""

    # ── Signals ──────────────────────────────────────────────
    sig_log = pyqtSignal(str, str)  # (sender, nachricht)
    sig_connected = pyqtSignal()  # Kanal offen
    sig_disconnected = pyqtSignal()  # Kanal geschlossen
    sig_offer_ready = pyqtSignal()  # Offer generiert
    sig_error = pyqtSignal(str)  # Fehlermeldung
    sig_file_received = pyqtSignal(str, str, int, bytes)

    def __init__(self) -> None:
        super().__init__()
        self.pc = None
        self.channel = None
        self._receiver = ft.FileReceiver()
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._loop.run_forever, daemon=True).start()

    def submit(self, coro) -> None:
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    def send_client_message(self, msg: str) -> None:
        """Sendet eine Textnachricht an den Host (Thread-Safe!)."""

        def _do_send():
            if self.channel and self.channel.readyState == "open":
                self.channel.send(f"[User]: {msg}")

        self._loop.call_soon_threadsafe(_do_send)

    # ── WebRTC Verbindungsaufbau ─────────────────────────────

    async def generate_offer(self) -> None:
        """Schritt 1: Erstellt DataChannel und generiert das Offer."""
        try:
            self.pc = RTCPeerConnection(configuration=STUN_SERVER)

            # WICHTIG: Client muss den Kanal vor dem Offer erstellen!
            self.channel = self.pc.createDataChannel("chat")
            self._register_datachannel_events()

            await self.pc.setLocalDescription(await self.pc.createOffer())
            await asyncio.sleep(2)  # Warten auf ICE-Candidates

            offer_str = json.dumps({
                "sdp": self.pc.localDescription.sdp,
                "type": self.pc.localDescription.type,
            })
            pyperclip.copy(offer_str)
            self.sig_offer_ready.emit()
            self.sig_log.emit("SYSTEM", "✅ Offer kopiert — gib es dem Host.")

        except Exception as exc:
            self.sig_error.emit(f"Offer-Fehler: {exc}")

    async def apply_answer(self, answer_dict: dict) -> None:
        """Schritt 2: Wendet die Answer des Hosts an."""
        try:
            await self.pc.setRemoteDescription(
                RTCSessionDescription(sdp=answer_dict["sdp"], type=answer_dict["type"])
            )
        except Exception as exc:
            self.sig_error.emit(f"Answer-Fehler: {exc}")

    # ── Datei senden ─────────────────────────────────────────

    async def send_file(self, filepath: str) -> None:
        """Sendet eine Datei in Chunks an den Host."""
        if not self.channel or self.channel.readyState != "open":
            self.sig_error.emit("Keine Verbindung zum Host.")
            return

        try:
            name = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                file_data = f.read()
            size = len(file_data)
            file_id = ft.generate_id()

            # Lokal in der Client-UI anzeigen
            self.sig_file_received.emit("ME", name, size, file_data)

            self.channel.send(ft.encode_meta(file_id, name, size))
            await asyncio.sleep(0)

            for offset in range(0, size, ft.CHUNK_SIZE):
                chunk = file_data[offset: offset + ft.CHUNK_SIZE]
                self.channel.send(ft.encode_chunk(file_id, chunk))
                await asyncio.sleep(0)

            self.channel.send(ft.encode_end(file_id))
            self.sig_log.emit("SYSTEM", f"Datei '{name}' gesendet ({ft.format_size(size)}).")

        except Exception as exc:
            self.sig_error.emit(f"Fehler beim Senden: {exc}")

    # ── Private Hilfsmethoden ────────────────────────────────

    def _register_datachannel_events(self) -> None:
        @self.channel.on("open")
        def on_open():
            self.sig_connected.emit()
            self.sig_log.emit("SYSTEM", "★  Verbindung zum Host hergestellt!")

        @self.channel.on("close")
        def on_close():
            self.sig_disconnected.emit()
            self.sig_log.emit("SYSTEM", "Verbindung zum Host unterbrochen.")

        @self.channel.on("message")
        def on_message(msg):
            if ft.is_control(msg):
                self._handle_control(msg)
            elif ft.is_chunk(msg):
                file_id, chunk = ft.parse_chunk(msg)
                self._receiver.on_chunk(file_id, chunk)
            elif ft.is_chat(msg):
                clean = msg.replace("[Host]: ", "").replace("[User]: ", "")
                # Wenn es nicht von mir ist, ist es vom Host oder anderen Usern
                self.sig_log.emit("PEER", clean)

    def _handle_control(self, msg: str) -> None:
        try:
            data = ft.parse_control(msg)
        except Exception:
            return

        ctrl_type = data.get("type")
        if ctrl_type == "file_meta":
            self._receiver.on_meta(data)
        elif ctrl_type == "file_end":
            result = self._receiver.on_end(data.get("id", ""))
            if result:
                name, size, file_data = result
                self.sig_file_received.emit("PEER", name, size, file_data)
                self.sig_log.emit("SYSTEM", f"Datei '{name}' empfangen.")
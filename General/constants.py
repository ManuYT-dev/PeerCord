"""
constants.py — Gemeinsame Konstanten (Farben, Netzwerk-Config)
Discord Dark Theme Farbpalette
"""

from aiortc import RTCConfiguration, RTCIceServer

# ── WebRTC ───────────────────────────────────────────────────
STUN_SERVER = RTCConfiguration(
    iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])]
)

# ── Discord Dark Theme Farben ────────────────────────────────
C_BG_DARKEST = "#1E1F22"   # Tiefster Hintergrund (Serverliste)
C_BG_DARK    = "#2B2D31"   # Sidebar-Hintergrund
C_BG_MAIN    = "#313338"   # Haupt-Chat-Bereich
C_BG_INPUT   = "#383A40"   # Eingabefeld
C_BG_HOVER   = "#35373C"   # Hover-Zustand
C_BORDER     = "#1E1F22"   # Rahmen / Trennlinien

# ── Akzentfarben ─────────────────────────────────────────────
C_BLURPLE    = "#5865F2"   # Discord Blurple (Primär-Akzent)
C_BLURPLE_D  = "#4752C4"   # Blurple dunkel
C_BLURPLE_L  = "#7289DA"   # Blurple hell
C_GREEN      = "#23A55A"   # Online-Grün
C_YELLOW     = "#F0B232"   # Idle-Gelb
C_RED        = "#ED4245"   # Rot (Fehler / Schließen)

# ── Textfarben ───────────────────────────────────────────────
C_TEXT_PRI   = "#DBDEE1"   # Primärtext
C_TEXT_SEC   = "#B5BAC1"   # Sekundärtext
C_TEXT_MUT   = "#80848E"   # Gedämpfter Text
C_TEXT_WHITE = "#FFFFFF"   # Reines Weiß (Hervorhebungen)

# ── Nachrichten-Farben ───────────────────────────────────────
C_HOST_COL   = "#5865F2"   # Blurple für Host
C_USER_COL   = "#3BA55D"   # Grün für User
C_SYS_COL    = "#80848E"   # Grau für System-Meldungen

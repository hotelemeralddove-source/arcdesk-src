"""One Arc Desk at a time.

The launcher makes double-starts likely: the wake daemon starts the app, and the
user may also double-click the shortcut a second later. Two reactors, two mic
listeners and two magic screens fighting over one wallpaper is exactly the kind
of bug that looks like a crash.

How it works, with no extra dependency:

  * the first instance binds ``127.0.0.1:<wake_port + 1>`` and keeps it open
  * a later instance cannot bind it, so it sends ``{"event": "wake"}`` to the
    owner and exits quietly
  * the owner turns that into the normal fullscreen "HEY JARVIS" arrival

That means saying "Hey Jarvis" while the app is already running no longer risks
a second copy — it just comes to the front.
"""
from __future__ import annotations

import json
import socket
import threading
from typing import Callable

LIVE = threading.Event()


def lock_port(cfg: dict) -> int:
    inst = cfg.get("instance", {}) or {}
    explicit = int(inst.get("port", 0) or 0)
    if explicit:
        return explicit
    wake = int((cfg.get("wake", {}) or {}).get("port", 8765) or 8765)
    return min(wake + 1, 65534)


def _send_wake(port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
            s.sendall(json.dumps({"event": "wake", "from": "second-instance"}
                                 ).encode("utf-8") + b"\n")
        return True
    except OSError:
        return False


class Instance:
    """Holds the listening socket for the lifetime of the process."""

    def __init__(self, cfg: dict, on_summon: Callable[[], None] | None = None):
        self.port = lock_port(cfg)
        self.on_summon = on_summon
        self.sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    # ------------------------------------------------------------- lifecycle
    def acquire(self) -> bool:
        """True if we are the first instance, False if one already exists."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", self.port))
            s.listen(2)
        except OSError:
            s.close()
            return False
        self.sock = s
        LIVE.set()
        self._thread = threading.Thread(target=self._serve, name="instance",
                                        daemon=True)
        self._thread.start()
        return True

    def _serve(self) -> None:
        assert self.sock is not None
        self.sock.settimeout(0.5)
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.settimeout(0.5)
                data = b""
                while b"\n" not in data and len(data) < 4096:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                event = json.loads(data.decode("utf-8", "replace") or "{}").get("event")
                if event in ("wake", "show") and self.on_summon:
                    self.on_summon()
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    def release(self) -> None:
        self._stop.set()
        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        LIVE.clear()


def another_instance_running(cfg: dict) -> bool:
    """True when a second copy exists *and* has been told to wake up."""
    return _send_wake(lock_port(cfg))


def is_live() -> bool:
    return LIVE.is_set()

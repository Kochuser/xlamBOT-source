"""Reuse immutable ONNX weights; observations and detector buffers stay local."""
import hashlib
import os
import threading
import weakref

_LOCK = threading.RLock()
_SESSIONS = weakref.WeakValueDictionary()


def _digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.digest()


def acquire(path, providers, threads, factory):
    """Load one live session per model contents and execution configuration."""
    resolved = os.path.normcase(os.path.realpath(path))
    fingerprint = _digest(resolved)
    key = (resolved, fingerprint, tuple(providers), int(threads))
    with _LOCK:
        session = _SESSIONS.get(key)
        if session is not None:
            return session, True
        session = factory()
        # Atomic replacement while the runtime reads the file must never bind
        # weights from a different revision to the earlier fingerprint.
        if _digest(resolved) == fingerprint:
            _SESSIONS[key] = session
        return session, False

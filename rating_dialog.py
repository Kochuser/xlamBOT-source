"""Confirm the native rating dialog and locate its non-review action."""
from functools import lru_cache
import base64
import cv2
import numpy as np
from rating_dialog_glyphs import TITLE, LATER


@lru_cache(maxsize=24)
def _glyph(encoded, height):
    mask = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), 0)
    return cv2.resize(mask, (max(2, round(mask.shape[1]*height/720)),
                             max(2, round(mask.shape[0]*height/720))))


def _locate(mask, glyph):
    if not mask.size or any(mask.shape[i] < glyph.shape[i] for i in (0, 1)):
        return None
    # A one-pixel resampling phase must not turn the same native caption into
    # a different glyph. Preserve the caption geometry and high confidence.
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    glyph = cv2.GaussianBlur(glyph, (3, 3), 0)
    _, score, _, position = cv2.minMaxLoc(cv2.matchTemplate(mask, glyph, cv2.TM_CCOEFF_NORMED))
    return position if score >= .92 else None


def rating_later_position(frame):
    """Require the title, neutral modal body and the actual LATER caption."""
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        return None
    h, w = frame.shape[:2]
    if h < 180 or w < h:
        return None
    scale = h/720
    left = max(0, round(w/2-328*scale))
    right = min(w, round(w/2+328*scale))
    body = frame[round(h*.35):round(h*.65), left+round(24*scale):right-round(24*scale)].astype(np.int16)
    if not body.size:
        return None
    grey = (np.ptp(body, axis=2) < 10) & (body.mean(axis=2) > 32) & (body.mean(axis=2) < 95)
    if grey.mean() < .8:
        return None
    title = frame[round(h*.36):round(h*.45), left:right]
    white = np.all(title > 205, axis=2).astype(np.uint8)*255
    if _locate(white, _glyph(TITLE, h)) is None:
        return None
    top = round(h*.57)
    button = frame[top:round(h*.65), left:left+round(200*scale)].astype(np.int16)
    cyan = ((button[:,:,1] > 150) & (button[:,:,2] > 150) & (button[:,:,0] < 170)
            & (button[:,:,1]-button[:,:,0] > 20)).astype(np.uint8)*255
    glyph = _glyph(LATER, h)
    position = _locate(cyan, glyph)
    if position is None:
        return None
    return left+position[0]+glyph.shape[1]//2, top+position[1]+glyph.shape[0]//2

"""Recognize a team invitation without using the inviter's account details."""
from functools import lru_cache
import base64
import cv2
import numpy as np
from team_invite_glyphs import TITLE, REJECT


@lru_cache(maxsize=16)
def _glyph(encoded, height):
    raw = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), 0)
    return cv2.resize(raw, (max(2, round(raw.shape[1]*height/720)),
                            max(2, round(raw.shape[0]*height/720))))


def _locate(frame, encoded, bounds):
    h, w = frame.shape[:2]
    left, top, right, bottom = bounds
    left, right = round(w/2+left*h/720), round(w/2+right*h/720)
    top, bottom = round(top*h/720), round(bottom*h/720)
    if left < 0 or right > w:
        return None
    crop = frame[top:bottom, left:right]
    glyph = _glyph(encoded, h)
    if not crop.size or any(crop.shape[i] < glyph.shape[i] for i in (0, 1)):
        return None
    mask = np.all(crop > 205, axis=2).astype(np.uint8)*255
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    glyph = cv2.GaussianBlur(glyph, (3, 3), 0)
    _, score, _, point = cv2.minMaxLoc(cv2.matchTemplate(mask, glyph, cv2.TM_CCOEFF_NORMED))
    if score < .92:
        return None
    return left+point[0]+glyph.shape[1]//2, top+point[1]+glyph.shape[0]//2


def team_invite_reject_position(frame):
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
        return None
    h, w = frame.shape[:2]
    if h < 180 or w < h:
        return None
    left, right = round(w/2-268*h/720), round(w/2+268*h/720)
    header = frame[round(h*150/720):round(h*211/720), left:right]
    if not header.size:
        return None
    blue = (header[:,:,0] < 70) & (header[:,:,1] > 110) & (header[:,:,2] > 210)
    if blue.mean() < .75 or _locate(frame, TITLE, (-130,155,130,204)) is None:
        return None
    left, right = round(w/2-221*h/720), round(w/2-14*h/720)
    button = frame[round(h*425/720):round(h*478/720),left:right]
    red = (button[:,:,0] > 190) & (button[:,:,1] < 85) & (button[:,:,2] < 85)
    if not red.size or red.mean() < .65:
        return None
    return _locate(frame, REJECT, (-215,425,-12,478))

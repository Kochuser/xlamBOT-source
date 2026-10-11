"""Independent evidence for an epic skin awarded outside a reward sequence."""
import cv2
import numpy as np
from reward_receipts import _glyph, _find, _valid, CONTINUE
from new_skin_glyphs import NEW_EPIC, CURRENT


def _caption(frame, encoded, bounds, white):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bounds
    roi = frame[round(h*y1):round(h*y2), round(w*x1):round(w*x2)].astype(np.int16)
    if not roi.size:
        return False
    mask = (np.all(roi > 205, axis=2) if white else
            (roi[:,:,0] > 150) & (roi[:,:,2] > 170) & (roi[:,:,1] < 100))
    mask = cv2.GaussianBlur(mask.astype(np.uint8)*255, (3, 3), 0)
    glyph = cv2.GaussianBlur(_glyph(encoded, h), (3, 3), 0)
    if any(mask.shape[i] < glyph.shape[i] for i in (0, 1)):
        return False
    return cv2.minMaxLoc(cv2.matchTemplate(mask, glyph, cv2.TM_CCOEFF_NORMED))[1] >= .92


def new_skin_continue_position(frame):
    """Require NEW EPIC SKIN, current-skin label, backdrop and blue Continue."""
    if not _valid(frame):
        return None
    h, w = frame.shape[:2]
    margin = frame[round(h*.03):round(h*.25), :round(w*.10)].astype(np.float32)
    blue = (margin[:,:,2] > margin[:,:,0]*1.35) & (margin[:,:,2] > margin[:,:,1]*1.2)
    if not blue.size or blue.mean() < .9:
        return None
    if not _caption(frame, NEW_EPIC, (.47,.12,.95,.35), False):
        return None
    if not _caption(frame, CURRENT, (.54,0,.96,.10), True):
        return None
    position = _find(frame, CONTINUE, (.46,.8,.69,.92))
    if position is None:
        return None
    button = frame[round(h*.825):round(h*.89), round(w*.49):round(w*.665)]
    blue = (button[:,:,0] < 85) & (button[:,:,1] > 65) & (button[:,:,2] > 170)
    return position if blue.size and blue.mean() > .35 else None

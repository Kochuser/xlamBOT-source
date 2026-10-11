"""Positive evidence for the purple/orange spray reward receipt."""
import numpy as np
from reward_receipts import _valid, _find, REMAINING
from spray_receipt_glyph import SPRAY_TITLE


def spray_receipt(frame):
    if not _valid(frame):
        return False
    h, w = frame.shape[:2]
    left = frame[round(h*.25):round(h*.85), round(w*.03):round(w*.12)].astype(np.float32)
    right = frame[round(h*.25):round(h*.85), round(w*.82):round(w*.97)].astype(np.float32)
    purple = (left[:,:,2] > left[:,:,0]*1.10) & (left[:,:,2] > left[:,:,1]*1.15)
    orange = (right[:,:,0] > right[:,:,2]*1.05) & (right[:,:,0] > right[:,:,1]*1.12)
    if not purple.size or not orange.size or purple.mean() < .85 or orange.mean() < .85:
        return False
    if _find(frame, SPRAY_TITLE, (.35,.10,.65,.26)) is None:
        return False
    if _find(frame, REMAINING, (.65,.90,.95,1)) is None:
        return False
    counter = frame[round(h*.89):round(h*.97), round(w*.923):round(w*.967)]
    red = (counter[:,:,0] > 180) & (counter[:,:,1] < 100) & (counter[:,:,2] < 100)
    white = np.all(counter > 205, axis=2)
    if not red.size or red.mean() < .45 or white.mean() < .025:
        return False
    item = frame[round(h*.32):round(h*.72), round(w*.34):round(w*.66)]
    dark = np.all(item < 65, axis=2)
    return bool(dark.size and .025 < dark.mean() < .6)

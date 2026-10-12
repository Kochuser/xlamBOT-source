"""Positive evidence for a star-power item in the blue reward sequence."""
import numpy as np
from reward_receipts import _valid, _find, REMAINING
from star_power_glyph import STAR_POWER_TITLE


def star_power_receipt(frame):
    if not _valid(frame) or not frame.size:
        return False
    h,w=frame.shape[:2]
    # The gold medal is on the left, unlike the centered generic item reveal.
    medal=frame[round(h*.29):round(h*.71),round(w*.065):round(w*.335)]
    gold=(medal[:,:,0]>175)&(medal[:,:,1]>105)&(medal[:,:,2]<85)
    if not gold.size or gold.mean()<.20:
        return False
    for bounds in ((.03,.03,.43,.20),(.05,.76,.85,.88)):
        x1,y1,x2,y2=bounds
        patch=frame[round(h*y1):round(h*y2),round(w*x1):round(w*x2)].astype(np.float32)
        blue=(patch[:,:,2]>patch[:,:,0]*1.3)&(patch[:,:,2]>patch[:,:,1]*1.12)
        if not blue.size or blue.mean()<.90:
            return False
    if _find(frame,STAR_POWER_TITLE,(.45,.18,.92,.36)) is None:
        return False
    if _find(frame,REMAINING,(.65,.90,.98,1)) is None:
        return False
    counter=frame[round(h*.89):round(h*.97),round(w*.923):round(w*.967)]
    red=(counter[:,:,0]>180)&(counter[:,:,1]<100)&(counter[:,:,2]<100)
    white=np.all(counter>205,axis=2)
    return bool(red.size and red.mean()>.45 and white.mean()>.025)

"""Independently recognize a completed blue brawler-unlock reward receipt."""
import base64
from functools import lru_cache
import cv2
import numpy as np
from unlocked_receipt_glyphs import HEADER, UNLOCKED


@lru_cache(maxsize=24)
def _glyph(encoded,height):
    raw=cv2.imdecode(np.frombuffer(base64.b64decode(encoded),np.uint8),0)
    return cv2.resize(raw,(max(2,round(raw.shape[1]*height/720)),
                          max(2,round(raw.shape[0]*height/720))),interpolation=cv2.INTER_NEAREST)


def _caption(frame,encoded,bounds,yellow=False):
    h,w=frame.shape[:2]
    left,top,right,bottom=bounds
    crop=frame[round(h*top):round(h*bottom),round(w*left):round(w*right)]
    if not crop.size:return False
    if yellow:
        mask=(crop[:,:,0]>220)&(crop[:,:,1]>185)&(crop[:,:,2]<100)
    else:
        mask=(crop[:,:,0]<150)&(crop[:,:,1]>180)&(crop[:,:,2]>200)
    glyph=_glyph(encoded,h)
    if any(crop.shape[i]<glyph.shape[i] for i in (0,1)):return False
    score=cv2.minMaxLoc(cv2.matchTemplate(mask.astype(np.uint8)*255,glyph,cv2.TM_CCOEFF_NORMED))[1]
    return bool(np.isfinite(score) and score>=.90)


def unlocked_receipt(frame):
    if frame is None or frame.ndim!=3 or frame.shape[2]!=3:return False
    if not _caption(frame,HEADER,(.38,.15,.63,.255)):return False
    if not _caption(frame,UNLOCKED,(.38,.56,.63,.665),yellow=True):return False
    h,w=frame.shape[:2]
    # The receipt is a blue full-screen reward, not a modal or a brawler preview.
    background=frame[round(h*.70):round(h*.95),round(w*.12):round(w*.88)]
    if not background.size:return False
    hsv=cv2.cvtColor(background,cv2.COLOR_RGB2HSV)
    blue=cv2.inRange(hsv,np.array([95,140,135]),np.array([125,255,255]))
    if np.mean(blue>0)<.90:return False
    portrait=frame[round(h*.37):round(h*.46),round(w*.434):round(w*.443)]
    if not portrait.size:return False
    cyan=((portrait[:,:,0]>90)&(portrait[:,:,1]>180)&(portrait[:,:,2]>190)&
          (portrait[:,:,1].astype(np.int16)-portrait[:,:,0]>25))
    if np.mean(cyan)<.65:return False
    # Confirm the central portrait footer independently of the brawler's name.
    footer=frame[round(h*.495):round(h*.552),round(w*.438):round(w*.565)]
    if not footer.size or np.mean(np.all(footer<55,axis=2))<.55:return False
    return True

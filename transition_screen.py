"""Positive noninteractive transition screens avoid unrelated menu searches."""
from functools import lru_cache
import base64
import cv2
import numpy as np
from transition_glyphs import LOGO, PERCENT, VERSUS, INTRO_CAPTION, BAR_CAP


@lru_cache(maxsize=24)
def _glyph(encoded, height):
    raw=cv2.imdecode(np.frombuffer(base64.b64decode(encoded),np.uint8),0)
    return cv2.resize(raw,(max(2,round(raw.shape[1]*height/720)),max(2,round(raw.shape[0]*height/720))))


def _visible(frame, encoded, bounds, dark=False):
    h,w=frame.shape[:2];x1,y1,x2,y2=bounds
    crop=frame[round(h*y1):round(h*y2),round(w*x1):round(w*x2)]
    glyph=_glyph(encoded,h)
    if not crop.size or any(crop.shape[i]<glyph.shape[i] for i in (0,1)):
        return False
    # Include antialiased dark outline pixels after display resampling.
    mask=np.all(crop<45 if dark else crop>205,axis=2).astype(np.uint8)*255
    if not np.any(mask):
        return False
    _,score,_,_=cv2.minMaxLoc(cv2.matchTemplate(cv2.GaussianBlur(mask,(3,3),0),cv2.GaussianBlur(glyph,(3,3),0),cv2.TM_CCOEFF_NORMED))
    return score >= .94


def transition_state(frame):
    if not isinstance(frame,np.ndarray) or frame.ndim!=3 or frame.shape[2]!=3:
        return None
    h,w=frame.shape[:2]
    if h<180 or w<h:
        return None
    # Match the game logo and orange progress bar, plus either the percentage
    # caption or the exact slanted outline while the percentage fades out.
    # A logo or ordinary orange rectangle alone is insufficient.
    bar=frame[round(h*.905):round(h*.94),round(w*.375):round(w*.625)]
    orange=(bar[:,:,0]>190)&(bar[:,:,1]>65)&(bar[:,:,1]<170)&(bar[:,:,2]<75)
    if orange.size and orange.mean()>.15 and _visible(frame,LOGO,(0,0,.26,.26)):
        if (_visible(frame,PERCENT,(.43,.78,.59,.89))
                or _visible(frame,BAR_CAP,(.36,.88,.44,.98),dark=True)):
            return 'loading'
    if _visible(frame,VERSUS,(.43,.36,.57,.49)) and _visible(frame,INTRO_CAPTION,(.26,.87,.73,.98)):
        return 'match_intro'
    return None

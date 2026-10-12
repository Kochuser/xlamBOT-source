"""Positive control evidence for the duplicate-reward confirmation dialog."""
import cv2
import numpy as np
from alternative_reward_glyphs import HEADER,EXPLANATION,CLAIM
from seasonal_rewards import _glyph


def _caption(frame,encoded,bounds):
    h,w=frame.shape[:2];x1,y1,x2,y2=bounds
    left,top=round(w*x1),round(h*y1)
    crop=frame[top:round(h*y2),left:round(w*x2)]
    glyph=_glyph(encoded,h)
    if not crop.size or any(crop.shape[i]<glyph.shape[i] for i in (0,1)):return None
    white=np.all(crop>205,axis=2).astype(np.uint8)*255
    _,score,_,location=cv2.minMaxLoc(cv2.matchTemplate(white,glyph,cv2.TM_CCOEFF_NORMED))
    if score<.92:return None
    return left+location[0]+glyph.shape[1]//2,top+location[1]+glyph.shape[0]//2


def alternative_claim_position(frame):
    if frame is None or frame.ndim!=3 or frame.shape[2]!=3 or not frame.size:return None
    h,w=frame.shape[:2]
    # Dimmed outside terrain and the two blue modal sections are independent
    # of the captions; generic CLAIM controls in shop pages cannot pass.
    margin=frame[round(h*.3):round(h*.7),round(w*.03):round(w*.15)]
    if not margin.size or margin.mean()>85:return None
    for bounds in ((.27,.245,.73,.34),(.27,.36,.73,.72)):
        x1,y1,x2,y2=bounds;crop=frame[round(h*y1):round(h*y2),round(w*x1):round(w*x2)].astype(np.int16)
        blue=(crop[:,:,2]>185)&(crop[:,:,1]>65)&(crop[:,:,0]<90)
        if not blue.size or blue.mean()<.65:return None
    if _caption(frame,HEADER,(.30,.245,.70,.33)) is None:return None
    if _caption(frame,EXPLANATION,(.275,.425,.725,.525)) is None:return None
    button=frame[round(h*.62):round(h*.70),round(w*.42):round(w*.58)].astype(np.int16)
    blue=(button[:,:,2]>185)&(button[:,:,1]>65)&(button[:,:,0]<90)
    if not blue.size or blue.mean()<.65:return None
    return _caption(frame,CLAIM,(.42,.62,.58,.70))

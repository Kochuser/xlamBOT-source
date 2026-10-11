"""Positive control evidence for the free Brawler Blast reward gallery."""
import cv2
import numpy as np
from reward_receipts import _glyph, _valid
from brawler_blast_glyphs import TAP, ARROW, BONUS, LEFT_GUN, RIGHT_GUN, DOME, DOME_GLOW, DOME_PULSE


def _find(frame, encoded, bounds, pink=False):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = bounds
    x, y = round(w*x1), round(h*y1)
    roi = frame[y:round(h*y2), x:round(w*x2)].astype(np.int16)
    mask = ((roi[:,:,0]>200)&(roi[:,:,2]>180)&(roi[:,:,1]<220) if pink
            else np.all(roi>235, axis=2))
    mask = cv2.GaussianBlur(mask.astype(np.uint8)*255, (3,3), 0)
    glyph = cv2.GaussianBlur(_glyph(encoded, h), (3,3), 0)
    if not mask.size or any(mask.shape[i]<glyph.shape[i] for i in (0,1)):
        return None
    _, score, _, position = cv2.minMaxLoc(cv2.matchTemplate(mask, glyph, cv2.TM_CCOEFF_NORMED))
    if score < .92:
        return None
    return (x+position[0]+glyph.shape[1]/2, y+position[1]+glyph.shape[0]/2)


def brawler_blast_fire_position(frame):
    """Find the verified gun control despite intermittently hidden TAP prompts."""
    if not _valid(frame):
        return None
    h, w = frame.shape[:2]
    background = frame[:round(h*.17), :round(w*.14)].astype(np.float32)
    purple = (background[:,:,2]>background[:,:,1]*1.15)&(background[:,:,0]>background[:,:,1]*1.12)
    if not purple.size or purple.mean()<.85:
        return None
    gallery_control = _gallery_control(frame)
    if gallery_control is not None:
        return gallery_control
    if _find(frame, BONUS, (.36,.87,.65,.99), True) is None:
        return None
    arrows = []
    for x1, x2 in ((.07,.2), (.81,.94)):
        if _find(frame, TAP, (x1,.34,x2,.49)) is None:
            return None
        arrow = _find(frame, ARROW, (x1,.45,x2,.57))
        if arrow is None:
            return None
        # The arrow identifies the visible yellow cap, not a decorative EXIT sign.
        cx, cy = arrow[0], arrow[1]+h*.06
        cap = frame[round(cy-h*.014):round(cy+h*.014), round(cx-w*.012):round(cx+w*.012)]
        if not cap.size or ((cap[:,:,0]>220)&(cap[:,:,1]>165)&(cap[:,:,2]<125)).mean()<.8:
            return None
        gun = frame[round(h*.63):round(h*.72), round(w*x1):round(w*x2)].astype(np.float32)
        blue = (gun[:,:,2]>gun[:,:,0]*1.2)&(gun[:,:,2]>gun[:,:,1]*1.05)
        if not blue.size or blue.mean()<.35:
            return None
        arrows.append((cx, cy))
    return arrows[0]


def _gallery_control(frame):
    h,w=frame.shape[:2]
    gray=cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY)
    left=None
    for variants,bounds in (((LEFT_GUN,),(0,.5,.21,.80)),((RIGHT_GUN,),(.79,.5,1,.80)),
                            ((DOME,DOME_GLOW,DOME_PULSE),(.39,.71,.46,.91))):
        x1,y1,x2,y2=bounds;x,y=round(w*x1),round(h*y1)
        roi=gray[y:round(h*y2),x:round(w*x2)]
        matched=None
        for encoded in variants:
            glyph=_glyph(encoded,h)
            if not roi.size or any(roi.shape[i]<glyph.shape[i] for i in (0,1)):
                continue
            _,score,_,position=cv2.minMaxLoc(cv2.matchTemplate(roi,glyph,cv2.TM_CCOEFF_NORMED))
            if score>=.95:
                matched=position
                break
        if matched is None:
            return None
        if variants==(LEFT_GUN,):
            left=(x+matched[0]+134*h/720,y+matched[1]+35*h/720)
    # Confirm the live yellow cap in RGB as well as the three independent graphics.
    cx,cy=left
    cap=frame[round(cy-h*.012):round(cy+h*.012),round(cx-h*.012):round(cx+h*.012)]
    if not cap.size or ((cap[:,:,0]>220)&(cap[:,:,1]>165)&(cap[:,:,2]<125)).mean()<.8:
        return None
    return left

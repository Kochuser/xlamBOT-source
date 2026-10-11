"""Positive evidence for the super-rare support unlock receipt."""
import cv2
import numpy as np
from support_receipt_glyphs import SUPER_RARE, SUPPORT, RIGHT_CONTINUE


def support_continue_position(frame):
    from new_brawler_receipt import _locate
    if not isinstance(frame,np.ndarray) or frame.ndim!=3 or frame.shape[2]!=3 or not frame.size:
        return None
    h,w=frame.shape[:2]
    if h<240 or w<320:
        return None
    # The rarity strip, role strip and ability circles are independent of the
    # character, its name and the reward animation in the lower-left corner.
    rarity=frame[round(h*.145):round(h*.225),round(w*.46):round(w*.635)]
    role=frame[round(h*.135):round(h*.225),round(w*.66):round(w*.825)]
    if not rarity.size or not role.size:
        return None
    cyan=(rarity[:,:,0]<70)&(rarity[:,:,1]>130)&(rarity[:,:,2]>180)
    dark=np.all(role<45,axis=2)
    if cyan.mean()<.35 or dark.mean()<.35:
        return None
    attack=frame[round(h*.345):round(h*.475),round(w*.90):round(w*.985)]
    super_button=frame[round(h*.49):round(h*.62),round(w*.91):round(w*.98)]
    red=(attack[:,:,0]>150)&(attack[:,:,1]<145)&(attack[:,:,2]<135)
    yellow=(super_button[:,:,0]>210)&(super_button[:,:,1]>115)&(super_button[:,:,2]<115)
    if not red.size or not yellow.size or red.mean()<.35 or yellow.mean()<.25:
        return None
    if _locate(frame,SUPER_RARE,(.45,.13,.64,.23)) is None:
        return None
    if _locate(frame,SUPPORT,(.68,.13,.83,.23)) is None:
        return None
    position=_locate(frame,RIGHT_CONTINUE,(.73,.79,.96,.91))
    if position is None:
        return None
    x,y=position
    patch=frame[max(0,y-round(h*.025)):min(h,y+round(h*.025)),
                max(0,x-round(w*.08)):min(w,x+round(w*.08))]
    hsv=cv2.cvtColor(patch,cv2.COLOR_RGB2HSV)
    blue=cv2.inRange(hsv,np.array([100,120,140]),np.array([125,255,255]))
    return position if np.mean(blue>0)>.30 else None

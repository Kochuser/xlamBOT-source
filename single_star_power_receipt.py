"""Recognize the full-screen star-power reward with a description card."""
import numpy as np
from reward_receipts import _valid, _find
from star_power_glyph import STAR_POWER_TITLE


def _text_band(patch,cyan=False):
    if not patch.size:return False
    if cyan:
        ink=(patch[:,:,0]<155)&(patch[:,:,1]>170)&(patch[:,:,2]>170)
    else:
        ink=np.all(patch>205,axis=2)
    if not .035<ink.mean()<.38:return False
    # Caption rows contain lettering and gaps, rather than a solid colored box.
    rows=ink.mean(axis=1)>.08
    return bool(rows.any() and (~rows).any())


def single_star_power_receipt(frame):
    if not _valid(frame) or not frame.size:return False
    h,w=frame.shape[:2]
    if _find(frame,STAR_POWER_TITLE,(.45,.18,.92,.36)) is None:return False
    medal=frame[round(h*.29):round(h*.71),round(w*.065):round(w*.335)]
    gold=(medal[:,:,0]>175)&(medal[:,:,1]>105)&(medal[:,:,2]<85)
    if not gold.size or gold.mean()<.20:return False
    for left,top,right,bottom in ((.03,.03,.43,.20),(.05,.76,.85,.88)):
        patch=frame[round(h*top):round(h*bottom),round(w*left):round(w*right)].astype(np.float32)
        blue=(patch[:,:,2]>patch[:,:,0]*1.3)&(patch[:,:,2]>patch[:,:,1]*1.12)
        if not blue.size or blue.mean()<.90:return False
    name=frame[round(h*.16):round(h*.225),round(w*.48):round(w*.88)]
    ability=frame[round(h*.335):round(h*.414),round(w*.47):round(w*.89)]
    if not _text_band(name) or not _text_band(ability,cyan=True):return False
    # Two continuous black borders and actual text on a dark description card
    # distinguish this reveal from an isolated heading or ordinary preview.
    for top,bottom in ((.432,.439),(.666,.673)):
        border=frame[round(h*top):round(h*bottom),round(w*.39):round(w*.96)]
        if not border.size or np.mean(np.all(border<55,axis=2))<.80:return False
    description=frame[round(h*.445):round(h*.655),round(w*.56):round(w*.955)]
    if not _text_band(description,cyan=True):return False
    if np.mean(np.all(description<125,axis=2))<.55:return False
    ink=(description[:,:,0]<155)&(description[:,:,1]>170)&(description[:,:,2]>170)
    occupied=ink.mean(axis=1)>.04
    line_starts=occupied & np.concatenate(([True],~occupied[:-1]))
    return bool(np.count_nonzero(line_starts)>=3)

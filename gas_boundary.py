"""Bounded clearance from the observed union of the closing gas front."""
import math
import cv2
import numpy as np


class GasBoundary:
    def __init__(self):
        self.reset()

    def reset(self):
        self.mask=None;self.field=None;self.stride=1;self.active=False
        self.report={'active':False,'reason':'unavailable'}

    def observe(self,mask,box,tile,blocked):
        if mask is None or box is None or len(box)<4:
            self.reset();return None
        h,w=mask.shape[:2]
        if not np.any(mask):
            self.reset();self.report={'active':False,'reason':'clear'};return None
        if self.mask is not mask:
            self.stride=max(1,math.ceil(max(h,w)/480))
            step=self.stride;anchor=step//2
            # Dilation before subsampling preserves even a one-pixel front.
            solid=cv2.dilate((mask>0).astype(np.uint8),np.ones((step,step),np.uint8))
            self.field=cv2.distanceTransform(1-solid[anchor::step,anchor::step],cv2.DIST_L2,3)*step
            self.mask=mask
        x1,y1,x2,y2=box;cx,cy=(x1+x2)/2,(y1+y2)/2
        radius=max(1.,min(x2-x1,y2-y1)/2)
        tile=max(radius,float(tile));margin=radius+tile*2
        def clearance(x,y):
            if not (radius<=x<w-radius and radius<=y<h-radius):return None
            row=min(self.field.shape[0]-1,int(y/self.stride));col=min(self.field.shape[1]-1,int(x/self.stride))
            return float(self.field[row,col])
        current=clearance(cx,cy)
        if current is None:
            self.active=False;self.report={'active':False,'reason':'unobserved_body'};return None
        visible=bool(np.any(mask))
        self.active=visible and current < margin+(tile if self.active else 0)
        self.report={'active':self.active,'clearance_px':round(current,1),'margin_px':round(margin,1),'reason':'front_nearby' if self.active else 'clear'}
        if not self.active:return None
        if current<=radius:
            # In existing gas, find a visible clean endpoint rather than using
            # the screen midpoint as a guessed world/map centre.
            closest=None
            for index in range(16):
                angle=index*math.pi/8;vector=(math.cos(angle),math.sin(angle))
                for distance in np.linspace(tile,min(w,h)*.65,20):
                    value=clearance(cx+vector[0]*distance,cy+vector[1]*distance)
                    if value is None:break
                    if value>=radius+tile*.5:
                        if (closest is None or distance<closest[0]) and not blocked(vector,float(distance)):
                            closest=(float(distance),vector)
                        break
            if closest is not None:
                distance,vector=closest
                self.report.update(direction=list(vector),exit_reach=distance/(radius*2),reason='leave_existing_gas')
                return vector
        best=None;best_score=current+self.stride
        for index in range(16):
            angle=index*math.pi/8;vector=(math.cos(angle),math.sin(angle))
            near=clearance(cx+vector[0]*tile,cy+vector[1]*tile)
            far=clearance(cx+vector[0]*tile*2,cy+vector[1]*tile*2)
            if near is None or far is None or near<current-self.stride:continue
            score=min(near,far)
            if score>best_score and not blocked(vector,tile*2):best_score=score;best=vector
        # At the deepest visible safe point in a narrow endgame zone, hold
        # position rather than oscillating or chasing a target into the front.
        vector=best or (0.,0.)
        self.report['direction']=list(vector)
        return vector

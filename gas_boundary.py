"""Bounded clearance from the observed union of the closing gas front."""
import math
import cv2
import numpy as np


class GasBoundary:
    def __init__(self):
        self.reset()

    def reset(self):
        self.mask=None;self.field=None;self.front_field=None;self.stride=1;self.active=False
        self.tile=None
        self.report={'active':False,'reason':'unavailable'}

    def observe(self,mask,box,tile,blocked):
        if mask is None or box is None or len(box)<4:
            self.reset();return None
        h,w=mask.shape[:2]
        if not np.any(mask):
            self.reset();self.report={'active':False,'reason':'clear'};return None
        x1,y1,x2,y2=box;cx,cy=(x1+x2)/2,(y1+y2)/2
        radius=max(1.,min(x2-x1,y2-y1)/2)
        tile=max(radius,float(tile));margin=radius+tile*2
        if self.mask is not mask or self.tile!=tile:
            self.stride=max(1,math.ceil(max(h,w)/480))
            step=self.stride;anchor=step//2
            # Dilation before subsampling preserves even a one-pixel front.
            solid=cv2.dilate((mask>0).astype(np.uint8),np.ones((step,step),np.uint8))
            reduced=solid[anchor::step,anchor::step]
            self.field=cv2.distanceTransform(1-reduced,cv2.DIST_L2,3)*step
            # The model can mark isolated bushes as gas. Only an observed
            # extended connected mass earns proactive clearance. All original
            # detections remain available for contact and final path guards.
            # Rendered clouds have gaps inside the same advancing mass. Join
            # neighbours at most one tile apart for qualification only; never
            # paint this dilation into the contact or swept-path detector mask.
            join=max(1,int(math.ceil(tile/(step*2))))
            grouped=cv2.dilate(reduced,np.ones((join*2+1,join*2+1),np.uint8))
            count,labels,_,_=cv2.connectedComponentsWithStats(grouped,8)
            accepted=np.zeros(count,np.uint8)
            minimum=max(4*tile,min(h,w)*.45)
            for index in range(1,count):
                rows,cols=np.nonzero((labels==index)&(reduced>0))
                if not rows.size:continue
                width=cols.max()-cols.min()+1;height=rows.max()-rows.min()+1
                if max(width,height)*step>=minimum and rows.size>=width*height*.12:
                    accepted[index]=1
            # Clearance includes the bounded gaps between qualified clouds:
            # the closing area is a mass, not navigable holes between sprites.
            front=accepted[labels]
            self.front_field=(cv2.distanceTransform(1-front,cv2.DIST_L2,3)*step
                              if np.any(front) else None)
            self.mask=mask;self.tile=tile
        # Keep emergency escape based on the complete detector mask, even if
        # the touching component is too small to establish a closing front.
        left,top=max(0,int(x1)),max(0,int(y1))
        right,bottom=min(w,int(math.ceil(x2))),min(h,int(math.ceil(y2)))
        body=mask[top:bottom,left:right]
        touching=body.size>0 and np.count_nonzero(body)/body.size>.05
        field=self.field if touching else self.front_field
        if field is None:
            self.active=False;self.report={'active':False,'reason':'isolated_detections'};return None
        def clearance(x,y):
            if not (radius<=x<w-radius and radius<=y<h-radius):return None
            row=min(field.shape[0]-1,int(y/self.stride));col=min(field.shape[1]-1,int(x/self.stride))
            return float(field[row,col])
        current=clearance(cx,cy)
        if current is None:
            self.active=False;self.report={'active':False,'reason':'unobserved_body'};return None
        visible=bool(np.any(mask))
        self.active=visible and current < margin+(tile if self.active else 0)
        self.report={'active':self.active,'clearance_px':round(current,1),'margin_px':round(margin,1),'reason':'front_nearby' if self.active else 'clear'}
        if not self.active:return None
        if touching and current<=radius:
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

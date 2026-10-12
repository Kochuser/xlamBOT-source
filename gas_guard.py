"""Coverage along a swept body path through the union of observed gas."""
import math
import numpy as np
import cv2

def coverage_integral(mask):
    return cv2.integral((mask>0).astype(np.uint8))


def corridor_peak(mask, box, vector, reach=3., integral=None):
    if mask is None or box is None:return 0.
    dx,dy=vector;length=math.hypot(dx,dy)
    if length<1e-6:return 0.
    dx,dy=dx/length,dy/length
    x1,y1,x2,y2=box;cx,cy=(x1+x2)/2,(y1+y2)/2
    radius=max(1.,min(x2-x1,y2-y1)/2)
    h,w=mask.shape[:2];peak=0.
    for distance in np.linspace(radius*.5,radius*2*reach,16):
        x,y=cx+dx*distance,cy+dy*distance
        # Unobserved ground past the screen is not a proven safe route.
        if x-radius<0 or y-radius<0 or x+radius>=w or y+radius>=h:return 1.
        left,top,right,bottom=round(x-radius),round(y-radius),min(w,round(x+radius)+1),min(h,round(y+radius)+1)
        if integral is None:
            share=float(np.mean(mask[top:bottom,left:right]>0))
        else:
            count=int(integral[bottom,right])-int(integral[top,right])-int(integral[bottom,left])+int(integral[top,left])
            share=count/((bottom-top)*(right-left))
        peak=max(peak,share)
    return peak


def improving_escape(mask,box,vector,reach=3.,integral=None):
    """Permit leaving existing gas only through a known, decreasing-risk path."""
    if mask is None or box is None:return False
    dx,dy=vector;length=math.hypot(dx,dy)
    if length<1e-6:return False
    dx,dy=dx/length,dy/length
    x1,y1,x2,y2=box;cx,cy=(x1+x2)/2,(y1+y2)/2
    radius=max(1.,min(x2-x1,y2-y1)/2);h,w=mask.shape[:2]
    if integral is None:integral=coverage_integral(mask)
    shares=[]
    samples=max(17,math.ceil(radius*2*reach/(radius*.5))+1)
    if samples>513:return False
    for distance in np.linspace(0,radius*2*reach,samples):
        x,y=cx+dx*distance,cy+dy*distance
        if x-radius<0 or y-radius<0 or x+radius>=w or y+radius>=h:return False
        left,top,right,bottom=round(x-radius),round(y-radius),round(x+radius)+1,round(y+radius)+1
        count=int(integral[bottom,right])-int(integral[top,right])-int(integral[bottom,left])+int(integral[top,left])
        shares.append(count/((bottom-top)*(right-left)))
    return (shares[0]>.05 and max(shares)<=shares[0]+.03
            and all(b<=a+.03 for a,b in zip(shares,shares[1:]))
            and shares[-1]<shares[0]-.05)

"""Conservative document portrait visibility using the local YuNet face detector.

No identity, portrait-replacement, or document-authenticity conclusion is made.
A missed face or detected candidate is only a visibility observation.
"""
from __future__ import annotations
import math
import cv2
import numpy as np
from PIL import Image
from portrait_face_comparison import DETECTOR

METHOD='opencv_yunet_portrait_visibility_v2'

def _result(status,finding,message,width,height,regions=None,quality=None,detected_count=None):
    boxes=regions or []
    return {'status':status,'finding':finding,'method':METHOD,
            'faces_detected':detected_count if detected_count is not None else len(boxes),
            'image_width':width,'image_height':height,'top_regions':boxes,
            'overlay_available':bool(boxes),'quality_observations':quality or {},
            'identity_verified':False,'portrait_replacement_detected':None,'message':message}

def review_document_portrait(image: Image.Image) -> dict:
    width,height=image.size
    if width<=0 or height<=0:
        return _result('not_assessed','invalid_image','Image is empty.',0,0)
    if not DETECTOR.is_file():
        return _result('unavailable','detector_unavailable','Local YuNet face detector is unavailable.',width,height)
    try:
        rgb=np.asarray(image.convert('RGB'))
        scale=min(1.0,1200.0/max(width,height))
        if scale<1.0:
            rgb=cv2.resize(rgb,(max(1,round(width*scale)),max(1,round(height*scale))),interpolation=cv2.INTER_AREA)
        bgr=cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR); h,w=bgr.shape[:2]
        detector=cv2.FaceDetectorYN_create(str(DETECTOR),'',(w,h),score_threshold=0.90,nms_threshold=0.3,top_k=100)
        detector.setInputSize((w,h)); _,faces=detector.detect(bgr)
        if faces is None or len(faces)==0:
            return _result('not_assessed','no_frontal_face_candidate','No high-confidence frontal face candidate was found; this does not establish that the document lacks a portrait.',width,height)
        valid=[]
        for face in faces:
            x,y,bw,bh=map(float,face[:4]); score=float(face[14]) if len(face)>14 else 0.0
            area=(bw*bh)/(w*h)
            if not all(math.isfinite(v) for v in (x,y,bw,bh,score,area)): continue
            if bw<40 or bh<40 or area<0.003 or area>0.55 or score<0.90: continue
            valid.append((x,y,bw,bh,score))
        if not valid:
            return _result('not_assessed','no_usable_face_candidate','Detector responses did not pass bounded size/confidence checks.',width,height,detected_count=0)
        valid.sort(key=lambda r:r[4],reverse=True)
        regions=[]
        for x,y,bw,bh,score in valid[:3]:
            regions.append({'x':round(x/w,6),'y':round(y/h,6),'width':round(bw/w,6),'height':round(bh/h,6),
                            'label':'frontal_face_candidate','detector_score':round(score,4)})
        x,y,bw,bh,_=valid[0]
        gray=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
        x0=max(0,int(x));y0=max(0,int(y));x1=min(w,int(x+bw));y1=min(h,int(y+bh));crop=gray[y0:y1,x0:x1]
        quality={}
        if crop.size and crop.shape[0]>=2 and crop.shape[1]>=2:
            quality={'sharpness_laplacian_variance':round(float(cv2.Laplacian(crop,cv2.CV_64F).var()),2),
                     'mean_brightness_0_255':round(float(crop.mean()),2),
                     'contrast_std_0_255':round(float(crop.std()),2)}
        return _result('completed' if len(valid)==1 else 'ambiguous','frontal_face_candidate',
                       'YuNet located a high-confidence frontal-face candidate; measurements describe visibility only. No identity or replacement verdict.',
                       width,height,regions,quality,detected_count=len(valid))
    except (cv2.error,ValueError,TypeError,OverflowError,MemoryError):
        return _result('unavailable','analysis_error','Portrait-visibility analysis could not complete; no conclusion.',width,height)

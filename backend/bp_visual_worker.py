"""MIT-licensed independent visual candidate adapter for a research-only local demonstration.
Model: Thermostatic/community-forensics-low-quality-detector-2026-08.
Official preprocessing and frozen calibrator from publisher model card. Not proof of provenance.
"""
from __future__ import annotations
import hashlib, io, json, math, os, sys
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageOps
import numpy as np

REPO='Thermostatic/community-forensics-low-quality-detector-2026-08'
FILE='community_forensics_low_quality_fp16.onnx'
URL=f'https://huggingface.co/{REPO}/resolve/main/{FILE}'
SHA='88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17'
SIZE=43778110
MEAN=np.array([.485,.456,.406],dtype=np.float32).reshape(1,1,3)
STD=np.array([.229,.224,.225],dtype=np.float32).reshape(1,1,3)
A=.6352260751077209
B=-.2643220522904507
PUBLISHER_THRESHOLD=.65

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def get_model(path):
    path=Path(path)
    if path.is_file():
        if path.stat().st_size!=SIZE or sha(path)!=SHA:
            raise RuntimeError('Cached model differs from publisher documented SHA-256; STOP')
        print('Verified cached model',file=sys.stderr,flush=True)
        return path
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.download')
    if tmp.exists():tmp.unlink()
    try:
        req=Request(URL,headers={'User-Agent':'BeyondPixels research local/1.0'})
        with urlopen(req,timeout=60) as response, tmp.open('wb') as out:
            if response.status!=200: raise RuntimeError('Model server non-200 response')
            n=0
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                n+=len(chunk)
                if n>SIZE:raise RuntimeError('Oversize model download')
                out.write(chunk)
        if n!=SIZE or sha(tmp)!=SHA:raise RuntimeError('Model checksum mismatch; STOP')
        os.replace(tmp,path)
    finally:
        if tmp.exists():tmp.unlink()
    print('Downloaded and verified publisher model',file=sys.stderr,flush=True)
    return path

def preprocess(blob):
    if not blob or len(blob)>8*1024*1024:raise ValueError('Image must be 1..8 MB')
    with Image.open(io.BytesIO(blob)) as im:
        if im.format not in ('JPEG','PNG'):raise ValueError('Only JPEG/PNG')
        if im.width<=0 or im.height<=0 or im.width*im.height>16_000_000:raise ValueError('Image pixel limit exceeded')
        im.load(); im=ImageOps.exif_transpose(im).convert('RGB')
    scale=440/min(im.size)
    im=im.resize((max(440,round(im.width*scale)),max(440,round(im.height*scale))),Image.Resampling.BICUBIC)
    left=(im.width-384)//2;top=(im.height-384)//2
    im=im.crop((left,top,left+384,top+384))
    rgb=np.asarray(im,dtype=np.float32)/255.
    return np.ascontiguousarray(((rgb-MEAN)/STD).transpose(2,0,1)[None])

def session(model):
    import onnxruntime as ort
    options=ort.SessionOptions();options.intra_op_num_threads=min(os.cpu_count() or 2,4)
    s=ort.InferenceSession(str(model),sess_options=options,providers=['CPUExecutionProvider'])
    inputs=s.get_inputs()
    if len(inputs)!=1 or inputs[0].type!='tensor(float)' or len(inputs[0].shape)!=4:
        raise RuntimeError('Unexpected model input signature')
    for actual,expected in zip(inputs[0].shape,(1,3,384,384)):
        if isinstance(actual,int) and actual!=expected:raise RuntimeError('Unexpected fixed model shape')
    if len(s.get_outputs())!=1:raise RuntimeError('Unexpected model output count')
    return s

def score(s, blob):
    output=np.asarray(s.run(None,{s.get_inputs()[0].name:preprocess(blob)})[0])
    if output.size!=1:raise RuntimeError('Expected one raw logit')
    logit=float(output.ravel()[0])
    if not math.isfinite(logit):raise RuntimeError('Nonfinite logit')
    x=A*logit+B
    prob=1/(1+math.exp(-x))
    return prob,logit

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Expected model path')
    try:
        s=session(get_model(Path(sys.argv[1])))
        p,raw=score(s,sys.stdin.buffer.read())
        sys.stdout.write(json.dumps({'score':round(p,8),'raw_logit':round(raw,8)}))
    except Exception as e:
        print(f'Visual worker failed: {type(e).__name__}: {e}',file=sys.stderr)
        sys.exit(1)

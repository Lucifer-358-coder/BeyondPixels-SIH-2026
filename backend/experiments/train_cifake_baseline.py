"""Train isolated BeyondPixels exploratory CIFAKE baseline. No writes to STAI source.

Existing feature CSV originates in CIFAKE TRAIN; 2k saved feature vectors originate
in a separately sampled CIFAKE test partition per STAI source scripts. We cannot
verify source-image identity without an image manifest, and this is NOT a document benchmark.
"""
from __future__ import annotations
import csv, json, pickle, hashlib, time
from pathlib import Path
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import confusion_matrix, roc_auc_score, precision_score, balanced_accuracy_score, brier_score_loss
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/cifake_training_data_5000_direct.csv'
OUT=ROOT/'models';OUT.mkdir(exist_ok=True)
COLUMNS=['grid_norm','radial_norm','kurtosis_norm','vanishing_norm','shadow_norm']
with DATA.open(newline='') as f:rows=list(csv.DictReader(f))
X=np.array([[float(row[c]) for c in COLUMNS] for row in rows],dtype=np.float64)
y=np.array([int(row['label']) for row in rows],dtype=int)
assert X.shape==(5000,5) and sorted(np.bincount(y).tolist())==[2500,2500]
assert np.isfinite(X).all() and np.min(X)>=0 and np.max(X)<=1
# Group identical rounded feature vectors, avoiding exact 4-decimal duplication across train/validation.
groups=[tuple(np.round(row,4)) for row in X]
ids={k:i for i,k in enumerate(dict.fromkeys(groups))}
gid=np.array([ids[k] for k in groups])
splitter=StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=20260918)
tr,va=next(splitter.split(X,y,groups=gid))
assert not set(gid[tr]).intersection(gid[va])
base=Pipeline([('scaler',StandardScaler()),('svm',SVC(kernel='rbf',C=1.0,class_weight='balanced'))])
model=CalibratedClassifierCV(estimator=base,method='sigmoid',cv=3)
t0=time.monotonic();model.fit(X[tr],y[tr]);elapsed=round(time.monotonic()-t0,3)
val=model.predict_proba(X[va])[:,list(model.classes_).index(1)]
# Select thresholds using ONLY validation set; require min 30 validation predictions,
# and >=90% measured precision for both predicted categories. This is NOT an
# operational certification; sampling uncertainty is still substantial.
def select_upper(scores,y,precision=.90,min_count=30):
 candidates=sorted(set(float(z) for z in scores))
 eligible=[(t,int((scores>=t).sum())) for t in candidates if (scores>=t).sum()>=min_count and y[scores>=t].mean()>=precision]
 return min((t for t,n in eligible),default=None)
def select_lower(scores,y,precision=.90,min_count=30):
 candidates=sorted(set(float(z) for z in scores))
 eligible=[(t,int((scores<=t).sum())) for t in candidates if (scores<=t).sum()>=min_count and (1-y[scores<=t]).mean()>=precision]
 return max((t for t,n in eligible),default=None)
lo=select_lower(val,y[va]);hi=select_upper(val,y[va])
if lo is not None and hi is not None and lo>=hi:
 raise RuntimeError('Inconsistent validation thresholds')
meta={
 'model_version':'cifake-feature-baseline-v0.1',
 'status':'research_only_not_validated_for_identity_documents',
 'source_dataset':'CIFAKE TRAIN feature vectors: 2500 REAL, 2500 FAKE',
 'source_csv_sha256':hashlib.sha256(DATA.read_bytes()).hexdigest(),
 'feature_order':COLUMNS,
 'training_samples':len(tr),'validation_samples':len(va),
 'validation_real':int((y[va]==0).sum()),'validation_ai':int((y[va]==1).sum()),
 'threshold_selection':'Validation subset only; >=90% empirical precision per chosen class, >=30 predictions; unachievable classes abstain',
 'low_not_ai_threshold':lo,'high_ai_threshold':hi,
 'validation_auc':float(roc_auc_score(y[va],val)),
 'validation_brier':float(brier_score_loss(y[va],val)),
 'training_seconds':elapsed,
 'limitations':['CIFAKE-only; 32x32 source domain; training feature CSV rounded to four decimals',
 'No verified image-level deduplication because training manifest unavailable',
 'No independently validated passport/document/screenshot or unseen-generator performance',
 'Scores are class-model estimates, not probabilities of identity authenticity or fraud'],
}
def evaluate(scores,actual,name):
 label=np.full(len(scores),2)
 if lo is not None:label[scores<=lo]=0
 if hi is not None:label[scores>=hi]=1
 decided=label!=2;cm=confusion_matrix(actual,label,labels=[0,1,2])[:2].tolist()
 return dict(name=name,samples=len(actual),auc=float(roc_auc_score(actual,scores)),brier=float(brier_score_loss(actual,scores)),coverage=float(decided.mean()),accuracy_on_decided=float((label[decided]==actual[decided]).mean()) if decided.any() else None,confusion_real_ai_by_pred_real_ai_inconclusive=cm,false_positive_rate_all_real=float(((label==1)&(actual==0)).sum()/(actual==0).sum()),false_negative_rate_all_ai=float(((label==0)&(actual==1)).sum()/(actual==1).sum()),inconclusive=int((label==2).sum()))
meta['validation_metrics']=evaluate(val,y[va],'validation')
test=np.load(ROOT/'data/cifake_test_2000_diagnostic.npz')
Xt=np.asarray(test['X'],dtype=np.float64);yt=np.asarray(test['actual'],dtype=int)
# Score the frozen test once; do not change thresholds based on its outcomes.
test_scores=model.predict_proba(Xt)[:,list(model.classes_).index(1)]
meta['saved_cifake_test_metrics']=evaluate(test_scores,yt,'saved_CIFAKE_test_2000')
model_bytes=pickle.dumps(model,protocol=pickle.HIGHEST_PROTOCOL)
meta['model_sha256']=hashlib.sha256(model_bytes).hexdigest()
(OUT/'beyondpixels_cifake_baseline.pkl').write_bytes(model_bytes)
(OUT/'beyondpixels_cifake_baseline.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'thresholds':{'not_ai_max':lo,'ai_min':hi},'validation':meta['validation_metrics'],'test':meta['saved_cifake_test_metrics'],'training_seconds':elapsed},indent=2))

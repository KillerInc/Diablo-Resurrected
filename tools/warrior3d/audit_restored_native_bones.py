"""Blender --python SCRIPT -- RESTORED_PLAN.json
Compare restored death/block channels with raw sampled source bone animation.
Closed finger poses are an approved grip choice; hands/wrists stay in the audit.
"""
import sys,json,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from merge_paladin_walk import read
from author_equipped_motion import tracks,blend
plan=json.loads(Path(sys.argv[sys.argv.index('--')+1]).read_text());reports=[]
for j in plan['jobs']:
 if j['action'] not in ['bl','dt']:continue
 model=Path(j['model']);spec=json.loads(model.with_suffix('.motion.json').read_text())['recipe'];g,b=read(model);sg,sb=read(spec['source']);actual=tracks(g,b);original=tracks(sg,sb);names={n.get('name'):i for i,n in enumerate(g['nodes'])}
 def branch(i):return {i}|set().union(*(branch(c) for c in g['nodes'][i].get('children',[])))
 excluded=set()
 for side in spec.get('finger_grip',[]):excluded|=branch(names['hand.'+side])-{names['hand.'+side],names['weapon.'+side]}
 def sample(i,path,frame):
  if (i,path) not in original:return np.array(sg['nodes'][i].get(path,{'translation':[0,0,0],'rotation':[0,0,0,1],'scale':[1,1,1]}[path]))
  times,values,method=original[i,path];t=frame/30;hi=int(np.searchsorted(times,t,side='right'))
  if hi==0:return values[0]
  if hi>=len(times):return values[-1]
  lo=hi-1;return blend(values[lo],values[hi],0 if method=='STEP' else float((t-times[lo])/(times[hi]-times[lo])),path)
 errors=[]
 for (i,path),(_,values,_) in actual.items():
  if i in excluded:continue
  for row,frame in enumerate(spec['frames']):
   expected=sample(i,path,frame);error=float(np.max(np.abs(values[row]-expected)))
   if path=='rotation':error=min(error,float(np.max(np.abs(values[row]+expected))))
   errors.append(error)
 maximum=max(errors,default=0);assert maximum<1e-5,(j['sheet'],maximum);reports.append({'sheet':j['sheet'],'source':spec['source'],'comparisons':len(errors),'maximum_native_channel_error':maximum,'finger_pose_excluded_only':True})
(Path(plan['work'])/'native-bone-audit.json').write_text(json.dumps(reports,indent=2));print('Verified complete native body/wrist channels for',len(reports),'death/block sheets')

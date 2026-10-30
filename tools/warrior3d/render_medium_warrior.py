"""Blender batch renderer for a prepared private medium plan; resumable outputs."""
import bpy,argparse,sys,json,runpy,subprocess,time,gc,hashlib,shutil,os
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('python',type=Path);p.add_argument('--only',nargs='+')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);file=a.plan.resolve();plan=json.loads(file.read_text());python=a.python.resolve();tools=Path(__file__).resolve().parent;progress_file=Path(plan['work'])/'render-progress.json';progress=json.loads(progress_file.read_text()) if progress_file.exists() else {};cache={}
priority=['wmnst','wmnwl','wmdat','wmuat','wmbat','wmtat','wmaat','wmndt','wmnfm','wmnlm','wmnqm'];jobs=sorted(plan['jobs'],key=lambda j:priority.index(j['sheet']) if j['sheet'] in priority else 99)
keys=['source_frames','rows','cell','equipment','root_anchor_frame','preserve_horizontal_root_motion','pose_offsets','direction_pose_offsets','redirect_fall','fire_effect','render_directions','sun_position','shadow_distance_gain','shadow_overscan','pose_image_offsets','direction_image_offsets','body_render_samples','shadow_render_samples']
def invoke(script,args):
 sys.argv=[str(script),'--',*map(str,args)];runpy.run_path(str(script),run_name='__main__')
def linktree(src,dst):
 for p in src.rglob('*'):
  target=dst/p.relative_to(src)
  if p.is_dir():target.mkdir(parents=True,exist_ok=True)
  elif not target.exists():
   target.parent.mkdir(parents=True,exist_ok=True)
   try:os.link(p,target)
   except OSError:shutil.copy2(p,target)
for number,j in enumerate(jobs,1):
 if a.only and j['sheet'] not in a.only:continue
 root=Path(j['root']);frames=root/'frames';shadows=root/'shadows';output=root/'output';ref=json.loads(Path(j['reference']).read_text());signature=hashlib.sha256(json.dumps([j['model'],{k:ref.get(k) for k in keys}],sort_keys=True).encode()).hexdigest();start=time.time()
 if (output/'validation.json').exists():
  progress[j['sheet']]={'status':'complete','validation':str(output/'validation.json')};cache[signature]=root;continue
 if signature in cache:
  previous=cache[signature];linktree(previous/'frames',frames);linktree(previous/'shadows',shadows)
  info=json.loads((frames/'render.json').read_text());info.update({k:ref[k] for k in ['sheet','canvas_logical','canvas_anchor','preview_prefix','preview_caption'] if k in ref})
  # Never write through the shared hard link to another job's metadata.
  (frames/'render.json').unlink();(frames/'render.json').write_text(json.dumps(info,indent=2))
 else:
  if not (frames/'render.json').exists():
   bpy.ops.wm.read_factory_settings(use_empty=False);invoke(tools/'render_paladin_town_walk.py',[j['model'],j['reference'],frames]);gc.collect()
  if not (shadows/'shadow.json').exists():invoke(tools/'render_paladin_shadows.py',[frames/'Paladin-town-walk-render.blend',frames/'render.json',shadows]);gc.collect()
 subprocess.run([str(python),str(tools/'assemble_paladin_canvas.py'),str(frames),str(shadows),str(frames/'render.json'),plan['calibration'],str(output)],check=True)
 cache[signature]=root;progress[j['sheet']]={'status':'complete','elapsed_seconds':round(time.time()-start,2),'validation':str(output/'validation.json')};progress_file.write_text(json.dumps(progress,indent=2));print('MEDIUM_COMPLETE',number,len(jobs),j['sheet'],progress[j['sheet']]['elapsed_seconds'],flush=True)
print('MEDIUM_BATCH_DONE',len(progress),flush=True)

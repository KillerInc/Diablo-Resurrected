"""Blender --python SCRIPT -- BASE_PLAN.json INSTALLED_LIMIT_AUDIT.json NEW_WORK
Undo only old canvas-fitting pose attenuation, preserving approved art choices.
Private inputs and generated artwork never belong in Git.
"""
import bpy,copy,json,sys,hashlib,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from author_equipped_motion import author
from full_motion_block_mount import hand_relative
basefile,auditfile,work=map(Path,sys.argv[sys.argv.index('--')+1:]);base=json.loads(basefile.read_text());audit=json.loads(auditfile.read_text());work=work.resolve();work.mkdir(parents=True,exist_ok=False);models=work/'models';models.mkdir();recipes=work/'recipes';recipes.mkdir();previous=Path(base['previous']);manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text());cache={};provenance=[]
controls=['arm_gain','motion_gain','wrist_gain','branch_gains','arm_tuck','weapon_envelope']
def restore(model):
 model=Path(model);key=str(model.resolve())
 if key in cache:return cache[key]
 metadata=model.with_suffix('.motion.json')
 if not metadata.exists():cache[key]=model;return model
 original=json.loads(metadata.read_text())['recipe'];spec=copy.deepcopy(original);spec['source']=str(restore(spec['source']))
 if spec.get('idle'):spec['idle']=str(restore(spec['idle']))
 for field in ['arms','node_overlays','world_arm_sources']:
  for overlay in spec.get(field,[]):
   if overlay.get('source'):overlay['source']=str(restore(overlay['source']))
 removed={k:spec.pop(k) for k in controls if k in spec}
 if spec.get('name','').endswith('-block'):
  native=next((a for a in spec.get('arms',[]) if a.get('side')=='L'),None)
  if native:spec.update(source=native['source'],frames=native['frames'],arms=[])
  spec['preserve_grip_wrist_motion']=True
 # No ordinary authoring differences require duplicating a native source.
 if spec==original:cache[key]=model;return model
 tag=model.stem+'-'+hashlib.sha256(key.encode()).hexdigest()[:8];recipe=recipes/(tag+'.json');recipe.write_text(json.dumps(spec,indent=2));dest=models/(tag+'.glb');author(recipe,dest);cache[key]=dest;provenance.append({'original_model':key,'restored_model':str(dest),'removed_canvas_controls':removed,'original_recipe':original,'restored_recipe':spec});return dest
targets=['wluas','wldaw','wluaw','wlhaw','wldbl','wlubl','wlhbl','wldht','wluht','wlhht','wlsht','wlmht']+[c+a for c in ['wld','wlu','wlh'] for a in ['fm','lm','qm']]+['wlndt']
plan=copy.deepcopy(base);plan.update(work=str(work),equipment_family='full-motion-restoration',restoration_targets=sorted(targets),starting_custom_manifest=manifest,starting_game_hashes={n:manifest['sheets'][n]['sha256'] for n in targets},jobs=[],copies=[],motions=[],inventory={},attack_action_frame=9,restore_unrestricted_motion=True)
for name in sorted(targets):
 code,action=name[:3],name[3:];p=Path(base['originals'])/code/(name+'.png')
 with p.open('rb') as f:f.seek(16);size=list(struct.unpack('>II',f.read(8)))
 data=(Path(base['cl2'])/code/(name+'.cl2')).read_bytes();rows=[struct.unpack_from('<I',data,o)[0] for o in struct.unpack_from('<8I',data)];assert len(set(rows))==1;rows=rows[0];plan['inventory'].setdefault(code,{})[name]={'original_size':size,'cell':size[0]//8,'rows':rows}
 if code in ['wlu','wlh'] and action in ['fm','lm','qm']:plan['copies'].append({'sheet':name,'source_sheet':'wld'+action});continue
 if name=='wlndt':
  native=previous/'paladin-native-death/faint/Paladin-animation.glb';assert native.is_file();spec={'name':'unrestricted native Paladin faint','source':str(native),'frames':[round(i*45/19) for i in range(20)],'arms':[]};recipe=recipes/'native-death.json';recipe.write_text(json.dumps(spec,indent=2));model=models/'native-death.glb';author(recipe,model);ref=json.loads((previous/'paladin-native-death/north-refinement/reference.json').read_text());provenance.append({'sheet':name,'native_source':str(native),'removed_render_controls':{k:ref[k] for k in ['redirect_fall','direction_pose_offsets','pose_image_offsets'] if k in ref}});ref['preserve_horizontal_root_motion']=True
 else:
  assert name in audit,name;entry=audit[name][0];model=restore(entry['model']);ref=json.loads(Path(entry['reference']).read_text())
 for field in ['redirect_fall','direction_pose_offsets','pose_image_offsets','pose_offsets','pose_xy_offsets','bounds','capture_bounds','render_rows']:ref.pop(field,None)
 if action=='bl':ref['equipment']=[hand_relative(e,previous/'paladin-sword-shield/Paladin-armed-idle-body.glb') if 'Shield_' in Path(e['path']).name else e for e in ref['equipment']]
 ref.update(sheet=name+'.png',rows=rows,cell=2048,source_frames=list(range(rows)),render_directions=list(range(8)),root_anchor_frame=0,canvas_logical=[320,256],canvas_anchor=[160,240],sun_position=[3,-4,6],shadow_distance_gain=1,shadow_overscan=512,preview_prefix=name,preview_caption=name.upper()+' | full motion / expanded canvas',preview_contact_row=min(rows-1,13 if action in ['fm','lm','qm'] else rows//2),preview_anchor=False)
 root=work/'jobs'/name;root.mkdir(parents=True);rp=root/'reference.json';rp.write_text(json.dumps(ref,indent=2));plan['jobs'].append({'sheet':name,'code':code,'action':action,'model':str(model),'root':str(root),'reference':str(rp),'motion':name});plan['motions'].append({'name':name})
(work/'restoration-provenance.json').write_text(json.dumps(provenance,indent=2));(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared',len(plan['jobs']),'full-motion renders and',len(plan['copies']),'spell aliases for',len(targets),'sheets')

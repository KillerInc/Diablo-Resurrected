"""Blender --background --python SCRIPT -- SHIELD_PLAN.json PRIVATE_TOWN_WORK
Use approved town poses; add belt-stowed sword/mace and carried axe/shield.
Run build_town_props.py for the private equipment directory first.
"""
import bpy,copy,json,sys,struct,hashlib,math
from pathlib import Path
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent));from author_equipped_motion import author
from merge_paladin_walk import read
source,work=map(Path,sys.argv[sys.argv.index('--')+1:]);base=json.loads(source.read_text());work=work.resolve();work.mkdir(exist_ok=True);assert not (work/'plan.json').exists();previous=Path(base['previous']);models=work/'models';models.mkdir(exist_ok=True);manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text());assets=Path(base['assets']);plan=copy.deepcopy(base);plan.update(work=str(work),equipment_family='light-town',town_equipment_revision=True,attack_action_frame=None,jobs=[],copies=[],motions=[],inventory={},starting_custom_manifest=manifest,starting_game_hashes={});plan.pop('shield_grip_correction',None);plan.pop('author_once',None)
body={}
for action,original,frames in [('st',previous/'paladin-town-idle/Paladin-D1-idle.glb',list(range(0,80,4))),('wl',previous/'paladin-short-stride-final/Paladin-short-stride.glb',list(range(0,40,5)))]:
 recipe={'name':'Approved town '+action,'source':str(original),'frames':frames,'arms':[]};rp=models/(action+'.json');rp.write_text(json.dumps(recipe,indent=2));model=models/(action+'.glb')
 if not model.exists():author(rp,model)
 body[False,action]=str(model)
doc,_=read(body[False,'st']);names={n.get('name'):i for i,n in enumerate(doc['nodes'])};indices=set()
def descendants(i):
 indices.add(i)
 for c in doc['nodes'][i].get('children',[]):descendants(c)
descendants(names['hand.R']);indices.discard(names['hand.R']);indices.discard(names['weapon.R']);fingers=sorted(doc['nodes'][i]['name'] for i in indices);axe_body={}
for action in ['st','wl']:
 rows=20 if action=='st' else 8;recipe={'name':'Town axe stable carrying grip '+action,'source':body[False,action],'frames':list(range(rows)),'arms':[],'idle':body[False,'st'],'wrist_gain':{'R':0},'node_overlays':[{'source':str(previous/'paladin-sword-shield/Paladin-armed-idle-body.glb'),'nodes':fingers,'frames':[0]*rows}]};rp=models/('axe-'+action+'.json');rp.write_text(json.dumps(recipe,indent=2));model=models/('axe-'+action+'.glb');author(rp,model);axe_body[action]=str(model)
st=next(j for j in base['jobs'] if j['sheet']=='wldst');wl=next(j for j in base['jobs'] if j['sheet']=='wluaw');body[True,'st']=st['model'];body[True,'wl']=wl['model'];shield=next(e for e in json.loads(Path(st['reference']).read_text())['equipment'] if 'Shield_' in e['path']);shield=copy.deepcopy(shield);shield['town_role']='carried_shield'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=body[False,'st']);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');bpy.context.scene.frame_set(0);bpy.context.view_layer.update();pelvis=rig.matrix_world@rig.pose.bones['pelvis'].matrix;hand=rig.matrix_world@rig.pose.bones['hand.R'].matrix

def oriented(shaft,normal,scale):
 y=Vector(shaft).normalized();z=Vector(normal);z=(z-y*z.dot(y)).normalized();x=y.cross(z).normalized();return Matrix((x,y,z)).transposed().to_4x4()@Matrix.Scale(scale,4)
def hip(offset,shaft,point,scale,normal=(-1,0,0)):
 world=oriented(shaft,normal,scale);world.translation=pelvis.translation+Vector(offset)-world.to_3x3()@Vector(point);return [list(r) for r in pelvis.inverted()@world]
sword=hip((.37,.18,-.12),(0,-.35,.93675),(0,0,0),.75,(1,0,0));mace=hip((-.35,-.20,.02),(0,-.20,.9799),(0,.18,0),.75);world=oriented((.25,.65,.71764),(-1,0,0),1);point=hand@Vector((.0425,.0825,-.002));world.translation=point-world.to_3x3()@Vector((0,-.85,0));axe=[list(r) for r in hand.inverted()@world];profiles={'sword':sword,'mace':mace,'axe':axe};(work/'town-mounts.json').write_text(json.dumps(profiles,indent=2));axe_path=Path(manifest['axe_sets']['archive'])/'Equipment/twoHandAxe_base01.glb';assert axe_path.is_file()
for code,kind,has_shield in [('wls','sword',False),('wld','sword',True),('wlm','mace',False),('wlh','mace',True),('wla','axe',False)]:
 plan['inventory'][code]={}
 for action in ['st','wl']:
  name=code+action;png=Path(plan['originals'])/code/(name+'.png');binary=(Path(plan['cl2'])/code/(name+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',binary,o)[0] for o in struct.unpack_from('<8I',binary)];assert len(set(counts))==1;rows=counts[0]
  with png.open('rb') as f:f.seek(16);size=list(struct.unpack('>II',f.read(8)))
  plan['inventory'][code][name]={'original_size':size,'cell':size[0]//8,'rows':rows};plan['starting_game_hashes'][name]=manifest['sheets'][name]['sha256'];gear=[]
  if kind=='sword':
   for path,role in [(assets/'sword_base00.glb','sheathed_sword'),(work/'equipment/TownSwordSheath.glb','sword_sheath')]:gear.append({'path':str(path),'bone':'pelvis','local_transform':sword,'town_role':role})
  elif kind=='mace':
   for path,role in [(assets/'mace_base03.glb','holstered_mace'),(work/'equipment/TownMaceFrog.glb','mace_frog')]:gear.append({'path':str(path),'bone':'pelvis','local_transform':mace,'town_role':role})
  else:gear=[{'path':str(axe_path),'bone':'hand.R','local_transform':axe,'grip':[0,-.85,0],'hand_point':[.0425,.0825,-.002],'town_role':'carried_axe'}]
  if has_shield:gear.append(copy.deepcopy(shield))
  root=work/'jobs'/name;root.mkdir(parents=True,exist_ok=True);ref={'sheet':name+'.png','rows':rows,'cell':1536,'columns':['S','SW','W','NW','N','NE','E','SE'],'source_frames':list(range(rows)),'render_directions':list(range(8)),'sun_position':[3,-4,6],'shadow_distance_gain':1,'shadow_overscan':512,'canvas_logical':[256,192],'canvas_anchor':[128,176],'capture_bounds':True,'root_anchor_frame':0,'preview_prefix':name,'preview_anchor':False,'preview_contact_row':0,'preview_caption':name.upper()+' | vanilla-style town equipment','equipment':gear};reference=root/'reference.json';reference.write_text(json.dumps(ref,indent=2));plan['jobs'].append({'sheet':name,'code':code,'action':action,'model':axe_body[action] if kind=='axe' else body[has_shield,action],'motion':name,'reference':str(reference),'root':str(root)});plan['motions'].append({'name':name})
(work/'plan.json').write_text(json.dumps(plan,indent=2));print('Prepared ten equipment-specific town sheets; existing shield-only and unarmed town sheets retained')

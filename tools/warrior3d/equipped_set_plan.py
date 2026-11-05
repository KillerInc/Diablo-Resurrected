"""Plan the actual light-warrior sword/shield sheet inventory from local assets.

Copyrighted models, references, animation data and outputs remain in the supplied
private work directories. Only authored recipes and tooling belong in Git.
"""
import copy,json,struct,hashlib
from pathlib import Path
from PIL import Image
from equipped_attack_recipe import make_attack_recipe,shield_attack_equipment
from shield_mount import correct as correct_shield_mount


def make_plan(work,previous,assets,originals,cl2,game,attack_canvas_profile=None):
 work,previous,assets,originals,cl2,game=map(lambda p:Path(p).resolve(),[work,previous,assets,originals,cl2,game]);work.mkdir(parents=True,exist_ok=True)
 assert not (work/'plan.json').exists(),'Plan already exists: resume its preflight/render or choose a new private work directory'
 attack_canvas=json.loads(Path(attack_canvas_profile).read_text()) if attack_canvas_profile else json.loads((Path(__file__).parent/'equipped_attack_canvas.json').read_text())
 manifest=json.loads((previous/'paladin-vanilla-dimensions/install-manifest.json').read_text());mounts=[correct_shield_mount(x) for x in json.loads((work/'approved-mounts.json').read_text())];inventory={};starting={}
 Image.MAX_IMAGE_PIXELS=None
 for code in ['wld','wls','wlu']:
  inventory[code]={}
  for png in sorted((originals/code).glob('*.png')):
   binary=(cl2/code/(png.stem+'.cl2')).read_bytes();counts=[struct.unpack_from('<I',binary,o)[0] for o in struct.unpack_from('<8I',binary)];assert len(set(counts))==1
   with Image.open(png) as im:size=list(im.size)
   cell=size[0]//8;assert size==[cell*8,cell*counts[0]]
   inventory[code][png.stem]={'size':size,'rows':counts[0],'cell':cell}
   if png.stem.endswith('at'):
    inventory[code][png.stem].update(original_size=size,canvas_logical=attack_canvas['logical'],canvas_anchor=attack_canvas['anchor'],size=[attack_canvas['logical'][0]*8*8,attack_canvas['logical'][1]*8*counts[0]])
   if png.stem in ['wldaw','wluaw','wldwl','wluwl','wldbl']:inventory[code][png.stem].update(canvas_logical=[98,96],canvas_anchor=[49,96],size=[98*64,96*8*counts[0]])
   live=game/'HD/plrgfx/warrior'/code/png.name;assert live.exists();starting[png.stem]=hashlib.sha256(live.read_bytes()).hexdigest().upper()
 assert [len(inventory[c]) for c in ['wld','wls','wlu']]==[10,9,10]
 source=work/'sources';recipes=work/'recipes';recipes.mkdir(exist_ok=True);models=work/'models';models.mkdir(exist_ok=True)
 idle_a=previous/'paladin-sword-shield/Paladin-armed-idle-body.glb';idle_u=previous/'paladin-town-idle/Paladin-D1-idle.glb';walk_u=previous/'paladin-short-stride-final/Paladin-short-stride.glb';hit_u=previous/'paladin-hit/Paladin-hit.glb';cast=previous/'paladin-fire-bubble/gizmo-final/Paladin-fire-cast.glb';punch=previous/'paladin-punch-fluid/Paladin-punch-fluid.glb'
 motions=[];jobs=[];copies=[]
 def motion(name,base,frames,arms=None,idle=None,grips=None,weights=None):
  recipe={'name':name,'source':str(base),'frames':list(frames),'arms':arms or [],'idle':str(idle or idle_a),'finger_grip':grips or [],'arm_gain':1,'motion_gain':1}
  if weights is not None:recipe['idle_weights']=weights
  path=recipes/(name+'.json');path.write_text(json.dumps(recipe,indent=2));model=models/(name+'.glb');motions.append({'name':name,'recipe':str(path),'model':str(model)});return model
 def arm(side,path,frames):return {'side':side,'source':str(path),'frames':list(frames)}
 def gear(code,action):
  if action in ['st','wl','fm','lm','qm']:return [copy.deepcopy(mounts[1])] if code in ('wld','wlu') else []
  return copy.deepcopy(mounts if code=='wld' else [mounts[0]] if code=='wls' else [mounts[1]])
 def job(sheet,model,motion_name,effect=None):
  code,action=sheet[:3],sheet[3:];inv=inventory[code][sheet];root=work/'jobs'/sheet;root.mkdir(parents=True,exist_ok=True);logical=inv['cell']//8
  ref={'sheet':sheet+'.png','rows':inv['rows'],'cell':inv['cell'],'columns':['S','SW','W','NW','N','NE','E','SE'],'source_frames':list(range(inv['rows'])),'sun_position':[3,-4,6],'shadow_distance_gain':1,'shadow_overscan':512,'canvas_logical':logical,'canvas_anchor':[logical//2,logical],'preview_prefix':sheet,'preview_anchor':False,'preview_contact_row':8 if action=='at' else min(inv['rows']-1,inv['rows']//2),'preview_caption':code.upper()+' '+action.upper()+' | approved S1 / H3 Red mounts','root_anchor_frame':0,'equipment':gear(code,action)}
  if inv.get('canvas_logical'):ref.update(canvas_logical=inv['canvas_logical'],canvas_anchor=inv['canvas_anchor'])
  if effect:ref['fire_effect']=effect
  if code=='wlu' and action=='at':ref['equipment']=shield_attack_equipment(ref['equipment']);ref.update(motion_root_bone='attach',native_root_drive=True,root_motion_scale=.45,root_motion_return=[1]*10+[.95,.8,.6,.4,.2,0])
  path=root/'reference.json';path.write_text(json.dumps(ref,indent=2));jobs.append({'sheet':sheet,'code':code,'action':action,'model':str(model),'motion':motion_name,'reference':str(path),'root':str(root)});return sheet
 def copy_sheet(sheet,source_sheet=None,path=None,crop_rows=None):copies.append({'sheet':sheet,'source_sheet':source_sheet,'path':str(path) if path else None,'crop_rows':crop_rows})
 # Resample the same combined idle body: its shield mount also needs correction.
 as_a=motion('combined-idle',idle_a,range(0,160,16),idle=idle_a);job('wldas',as_a,'combined-idle')
 as_s=motion('sword-idle',idle_a,range(0,160,16),[arm('L',idle_u,range(0,80,8))],grips=['R']);job('wlsas',as_s,'sword-idle')
 as_u=motion('shield-idle',idle_u,range(0,80,8),[arm('L',idle_a,range(0,160,16))],grips=['L']);job('wluas',as_u,'shield-idle')
 idles={'wld':idle_a,'wls':as_s,'wlu':as_u}
 for code in ['wld','wls','wlu']:
  both=code=='wld';sword=code in ['wld','wls'];grips=['R','L'] if both else ['R'] if sword else ['L']
  overlays=([arm('R',source/'walk-short.glb',range(0,40,5))] if sword else [])+([arm('L',source/'walk-short.glb',range(0,40,5))] if code!='wls' else [])
  base=walk_u;name=code+'-walk';model=motion(name,base,range(0,40,5),overlays,idles[code],grips);job(code+'aw',model,name)
  frames=[9*i/8 for i in range(9)]+[9+(59-9)*(i-8)/7 for i in range(9,16)]
  if sword:
   overlays=[] if both else [arm('L',idle_u,[0]*16)];base=source/'attack.glb'
  else:base=punch;frames=list(range(16));overlays=[arm('L',idle_a,[0]*16)]
  name=code+'-attack';model=motion(name,base,frames,overlays,idles[code],grips);attack_recipe=make_attack_recipe(code,idles[code],source/('sword-cut.glb' if sword else 'shield-charge.glb'),idle_u);(recipes/(name+'.json')).write_text(json.dumps(attack_recipe,indent=2));job(code+'at',model,name)
  frames=[0,4,8,13,19,25];overlays=[] if both else [arm('L' if sword else 'R',hit_u,frames)];name=code+'-hit';model=motion(name,source/'hit.glb',frames,overlays,idles[code],grips,[1,0,0,0,0,1]);job(code+'ht',model,name)
  if not code=='wls':
   name=code+'-block';model=motion(name,idles[code],[0,0],[arm('L',source/'block.glb',[6,14])],idles[code],grips);job(code+'bl',model,name)
 # In town the sword is not in hand; shield-bearing layouts share their pose.
 name='shield-town-idle';model=motion(name,idle_u,range(0,80,4),[arm('L',idle_a,range(0,160,8))],as_u,['L']);job('wldst',model,name);copy_sheet('wlust','wldst')
 copy_sheet('wldwl','wluaw');copy_sheet('wluwl','wluaw')
 for action in ['st','wl']:copy_sheet('wls'+action,path=manifest['sheets']['wln'+action]['source'])
 # Sword is absent from all original casting poses. Shield remains present.
 name='shield-cast';model=motion(name,cast,range(20),[arm('L',idle_a,[0]*20)],as_u,['L'])
 for action,folder in [('fm','paladin-fire-bubble/gizmo-final'),('lm','paladin-lightning'),('qm','paladin-magic/option2-ground-radius')]:
  effect=json.loads((previous/folder/'reference.json').read_text())['fire_effect'];job('wld'+action,model,name,effect);copy_sheet('wlu'+action,'wld'+action);copy_sheet('wls'+action,path=manifest['sheets']['wln'+action]['source'],crop_rows=20 if action=='lm' else None)
 # Preserve equipment-specific town carry/stow instead of reverting to unarmed aliases.
 if manifest.get('town_equipment_revision'):
  town={code+action for code in ['wld','wls','wlu'] for action in ['st','wl']};jobs[:]=[j for j in jobs if j['sheet'] not in town];copies[:]=[c for c in copies if c['sheet'] not in town]
  for name in sorted(town):
   record=manifest['sheets'][name];copy_sheet(name,path=record['source']);inventory[name[:3]][name].update(size=record['size'],canvas_anchor=list(map(int,record['layout'].split()[2:4])))
  active={j['motion'] for j in jobs};motions[:]=[m for m in motions if m['name'] in active]
 targets={j['sheet'] for j in jobs}|{c['sheet'] for c in copies};expected={k for sheets in inventory.values() for k in sheets};assert targets==expected and len(targets)==29
 result={'work':str(work),'previous':str(previous),'assets':str(assets),'originals':str(originals),'cl2':str(cl2),'game':str(game),'inventory':inventory,'starting_game_hashes':starting,'starting_custom_manifest':manifest,'motions':motions,'jobs':jobs,'copies':copies,'calibration':str(previous/'paladin-short-stride-final/output/validation.json'),'death_is_shared_unarmed':True,'attack_action_frame':9,'casting_action_frame':14}
 (work/'plan.json').write_text(json.dumps(result,indent=2));print('Planned',len(jobs),'render jobs and',len(copies),'validated copies/aliases for 29 sheets');return result


if __name__=='__main__':
 import sys
 make_plan(*sys.argv[1:])

"""Apply private measured building roof controls to an authoring candidate.

Arguments: converted-directory recipe.json output-directory
Keeps original source UVs; a separate UV layer carries the native reference.
The recipe is hash-bound to its input mesh archive and never edits a prefab.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

REFERENCE_UV='Native reference projection'


def interpolate(values, source, target):
    source,target=np.asarray(source),np.asarray(target)
    assert len(source)==len(target)>=2 and np.all(np.diff(source)>0) and np.all(np.diff(target)>0)
    result=np.interp(values,source,target)
    below,above=values<source[0],values>source[-1]
    result[below]=target[0]+(values[below]-source[0])*(target[1]-target[0])/(source[1]-source[0])
    result[above]=target[-1]+(values[above]-source[-1])*(target[-1]-target[-2])/(source[-1]-source[-2])
    return result


def deform(points, cage):
    result=points.copy()
    result[:,0]=interpolate(points[:,0],cage['source_x'],cage['target_x'])
    result[:,2]=interpolate(points[:,2],cage['source_z'],cage['target_z'])
    eave=np.interp(points[:,0],cage['source_x'],cage['target_eave_heights'])
    lower=points[:,1]<=cage['source_eave_height']
    result[lower,1]=points[lower,1]*eave[lower]/cage['source_eave_height']
    t=(points[~lower,1]-cage['source_eave_height'])/(cage['source_ridge_height']-cage['source_eave_height'])
    result[~lower,1]=eave[~lower]+t*(cage['target_ridge_height']-eave[~lower])
    assert np.isfinite(result).all()
    return result


def apply(args):
    source,output=args.source.resolve(),args.output.resolve()
    assert source!=output and not output.exists(),'Use a new candidate directory'
    recipe=json.loads(args.recipe.read_text())
    assert hashlib.sha256((source/'meshes.npz').read_bytes()).hexdigest()==recipe['mesh_sha256']
    scene=json.loads((source/'scene.json').read_text())
    meshes=np.load(source/'meshes.npz');archive={k:meshes[k].copy() for k in meshes.files}
    shutil.copytree(source,output)
    changed=[];references=[]
    for repair in recipe['repairs']:
        for entry in scene['meshes']:
            if entry.get('building')!=repair['id']:continue
            data=archive[entry['key']]
            original=data[:,:3].copy()
            data[:,:3]=deform(original,repair['cage'])
            assert np.array_equal(original[:,1]==0,data[:,1]==0)
            changed.append(entry['key'])
    for projection in recipe['references']:
        identity=projection['id']
        image=Path(projection['image']).resolve()
        filename=identity+'-measured-reference.png'
        shutil.copy2(image,output/'textures'/filename)
        with Image.open(image) as im:width,height=im.size
        for entry in scene['meshes']:
            if entry.get('building')!=identity:continue
            data=archive[entry['key']]
            points=data[:,:3]
            u=(32*(points[:,0]-points[:,2])-projection['world_pixel_origin'][0])/width
            v=(16*(points[:,0]+points[:,2])-32*points[:,1]-projection['world_pixel_origin'][1])/height
            archive[entry['key']]=np.column_stack((data[:,:5],u,v)).astype(np.float32)
            scene['materials'][entry['material']]['image']='textures/'+filename
            scene['materials'][entry['material']]['uv_map']=REFERENCE_UV
            references.append(entry['key'])
    np.savez_compressed(output/'meshes.npz',**archive)
    scene['measured_roof_repair']=dict(recipe=str(args.recipe.resolve()),geometry_meshes=changed,
                                      reference_uv_meshes=references,source_uvs_retained=True)
    (output/'scene.json').write_text(json.dumps(scene,indent=2))
    (output/'roof-repair.json').write_text(json.dumps(recipe,indent=2))
    print(json.dumps(scene['measured_roof_repair']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('source','recipe','output'):p.add_argument(field,type=Path)
    apply(p.parse_args())

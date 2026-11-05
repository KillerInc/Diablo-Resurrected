"""Gather registered RGB edits into a joint town/towns pixel address space.

Owner maps come from town_foreground.scene_region. Masks and view priority
are explicit authoring inputs. All RGBA geometry and hidden pixels stay exact.
"""
import numpy as np


def gather_scene(owners,rgb,mask=None):
    if owners.shape!=rgb.shape[:2]:raise ValueError('Scene dimensions changed')
    valid=owners>0
    if mask is not None:
        if mask.shape!=owners.shape:raise ValueError('Mask dimensions changed')
        valid&=mask
    positions=np.flatnonzero(valid)
    addresses=owners.ravel()[positions].astype(np.int64)-1
    addresses,first=np.unique(addresses,return_index=True)
    return addresses,rgb.reshape(-1,3)[positions[first]]


def apply_samples(terrain,foreground,addresses,rgb):
    count=terrain.shape[0]*terrain.shape[1]
    if len(addresses) and (addresses.min()<0 or addresses.max()>=count+foreground.shape[0]*foreground.shape[1]):
        raise ValueError('Scene owner outside sheets')
    if len(addresses)!=len(np.unique(addresses)):raise ValueError('Ambiguous repeated samples')
    for image,selected,offset in ((terrain,addresses<count,0),(foreground,addresses>=count,count)):
        positions=addresses[selected]-offset;flat=image.reshape(-1,4)
        if np.any(flat[positions,3]!=255):raise ValueError('Cannot repaint mixed-alpha/hidden pixels')
        flat[positions,:3]=rgb[selected]

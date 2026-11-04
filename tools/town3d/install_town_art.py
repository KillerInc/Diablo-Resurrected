"""Install a validated town-only art pack with a private rollback backup.

The installed index and layout are deliberately NOT rewritten. Every compiled
town frame/page record must match them exactly. Default is inspection only.
Close the game before --install; cached textures require a fresh process.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from PIL import Image
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gpu_index import read_index

Image.MAX_IMAGE_PIXELS=None


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def within(root,relative):
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Pack path escapes HD root')
    return path


def inspect(game,pack,source):
    key='levels/towndata/town.png'
    existing=read_index(game/'sprites.gpus');candidate=read_index(pack/'sprites.gpus')
    if key not in candidate or not set(candidate)<={key,'levels/towndata/towns.png'}:
        raise ValueError('Expected a town/foreground-only compiled pack')
    if any(candidate[k]!=existing[k] for k in candidate):raise ValueError('Native GPU metadata changed')
    if sha(game/'layouts.csv')!=sha(pack/'layouts.csv'):raise ValueError('Layout table changed')
    original=Image.open(game/key).convert('RGBA');new=Image.open(source).convert('RGBA')
    if original.size!=new.size or not np.array_equal(np.asarray(original)[:,:,3],np.asarray(new)[:,:,3]):
        raise ValueError('Native atlas geometry or alpha changed')
    files=[]
    for sheet,record in candidate.items():
        authored=source if sheet==key else source.with_name('towns.png')
        previous=Image.open(game/sheet).convert('RGBA');replacement=Image.open(authored).convert('RGBA')
        if previous.size!=replacement.size or not np.array_equal(np.asarray(previous)[:,:,3],np.asarray(replacement)[:,:,3]):
            raise ValueError('Native atlas geometry or alpha changed: '+sheet)
        pages=int(record[0].split()[-1])
        for line in record[1:1+pages]:
            name,w,h=line.split();rel=Path(sheet).parent/name
            old=within(game,rel);new_page=within(pack,rel)
            if old.stat().st_size!=new_page.stat().st_size:raise ValueError('Page storage size changed')
            files.append((new_page,old))
        files.append((authored,within(game,sheet)))
    report=dict(index_sha256=sha(game/'sprites.gpus'),layouts_sha256=sha(game/'layouts.csv'),
                metadata_identical=True,alpha_exact=True,files=[dict(source=str(a),destination=str(b),
                    before_sha256=sha(b),after_sha256=sha(a)) for a,b in files])
    return files,report


def install(args):
    files,report=inspect(args.game,args.pack,args.source)
    if not args.install:
        print(json.dumps(report,indent=2));return
    if args.backup is None or args.backup.exists():raise ValueError('A NEW private backup directory is required')
    if args.backup.resolve().is_relative_to(args.game.resolve()):raise ValueError('Keep backups outside game HD')
    args.backup.mkdir(parents=True);staged=[];replaced=[]
    try:
        for source,destination in files:
            saved=args.backup/destination.relative_to(args.game)
            saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(destination,saved)
            if sha(saved)!=sha(destination):raise IOError('Backup verification failed')
            temporary=destination.with_name(destination.name+'.town-art-new')
            if temporary.exists():raise ValueError('Stale installation staging file')
            shutil.copy2(source,temporary);staged.append(temporary)
            if sha(source)!=sha(temporary):raise IOError('Staging verification failed')
        for (_,destination),temporary in zip(files,staged):
            os.replace(temporary,destination);replaced.append(destination)
        for row in report['files']:
            if sha(Path(row['destination']))!=row['after_sha256']:raise IOError('Installation verification failed')
        if sha(args.game/'sprites.gpus')!=report['index_sha256'] or sha(args.game/'layouts.csv')!=report['layouts_sha256']:
            raise IOError('Installed metadata changed unexpectedly')
        report['installed']=True;report['backup']=str(args.backup.resolve())
        (args.backup/'installation.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(dict(installed=True,files=len(files),backup=report['backup'],metadata_identical=True)))
    except BaseException:
        for destination in reversed(replaced):
            shutil.copy2(args.backup/destination.relative_to(args.game),destination)
        raise
    finally:
        for temporary in staged:temporary.unlink(missing_ok=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game','pack','source'):p.add_argument(name,type=Path)
    p.add_argument('--backup',type=Path);p.add_argument('--install',action='store_true')
    install(p.parse_args())

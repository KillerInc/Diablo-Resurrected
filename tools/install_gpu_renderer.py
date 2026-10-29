"""Install validated compiled GPU assets and renderer; preserve original PNGs/CSV."""
import argparse,json,os,shutil
from pathlib import Path
from install_renderer_build import install as install_build
from install_layout_table import sha


def install(pack,binary,game,manifest,mirror,backup,validation):
    pack,binary,game,manifest,mirror,backup,validation=map(Path,(pack,binary,game,manifest,mirror,backup,validation))
    proof=json.loads(validation.read_text());assets=json.loads((pack/'validated-gpu-pack.json').read_text())
    assert proof['checks']['gpu_sprites'] and proof['gpu_sprites']['pack_file_hashes']==assets['files']
    assert proof['gpu_sprites']['texture_bytes']==assets['texture_bytes']
    assert sha(binary)==proof['executable_sha256']
    hd=(game/'HD').resolve();assert sha(hd/'layouts.csv')==assets['layout_sha256']
    for name,digest in assets['source_png_hashes'].items():assert sha(hd/name)==digest
    assert not backup.exists();backup.mkdir(parents=True)
    original_manifest,original_mirror=manifest.read_bytes(),mirror.read_bytes()
    written=[];existed={};temporaries=[]
    try:
        for name,digest in assets['files'].items():
            assert name.endswith(('.gpus','.bc7'))
            target=(hd/name).resolve();assert target.is_relative_to(hd)
            source=pack/'HD'/name;assert sha(source)==digest
            if target.exists() and sha(target)==digest:continue
            if target.exists():
                saved=backup/'gpu-before'/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);existed[name]=saved
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_name(target.name+'.gpu-new');assert not temporary.exists()
            temporaries.append(temporary);shutil.copy2(source,temporary);os.replace(temporary,target);written.append((name,target))
            assert sha(target)==digest
        # Retire only loose per-sheet metadata after the consolidated index is verified.
        if 'sprites.gpus' in assets['files']:
            for target in sorted((hd/'plrgfx').rglob('*.gpus')):
                target=target.resolve();assert target.is_relative_to(hd)
                name=target.relative_to(hd).as_posix()
                saved=backup/'gpu-before'/name;saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,saved);existed[name]=saved
                written.append((name,target));target.unlink()
        install_build(binary,game,manifest,mirror,backup/'renderer',validation)
        assert sha(hd/'layouts.csv')==assets['layout_sha256']
        for name,digest in assets['source_png_hashes'].items():assert sha(hd/name)==digest
        receipt={'version':proof['version'],'gpu_sheets':assets['sheets'],'pages':assets['pages'],'density':4,'texture_bytes':assets['texture_bytes'],'original_pngs_and_layouts_preserved':True,'executable_sha256':proof['executable_sha256'],'files':assets['files']}
        (backup/'gpu-install-receipt.json').write_text(json.dumps(receipt,indent=2))
        print('Installed',proof['version'],'with',assets['sheets'],'native 4x GPU sheets;',round(assets['texture_bytes']/2**30,3),'GiB BC7; original PNGs/CSV preserved')
    except BaseException:
        for name,target in reversed(written):
            assert target.is_relative_to(hd)
            if name in existed:shutil.copy2(existed[name],target)
            else:target.unlink(missing_ok=True)
        previous=list((backup/'renderer').glob('Diablo Reincarnated.before-*.exe')) if (backup/'renderer').exists() else []
        if previous:shutil.copy2(previous[0],game/'Diablo Reincarnated.exe')
        manifest.write_bytes(original_manifest);mirror.write_bytes(original_mirror)
        raise
    finally:
        for temporary in temporaries:temporary.unlink(missing_ok=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['pack','binary','game','manifest','mirror','backup','validation']:p.add_argument(name,type=Path)
    a=p.parse_args();install(a.pack,a.binary,a.game,a.manifest,a.mirror,a.backup,a.validation)

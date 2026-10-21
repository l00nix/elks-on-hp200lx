#!/usr/bin/env python3
"""Promote frozen FINAL2b and accepted images; never rebuild or modify them."""
from pathlib import Path
import hashlib, io, json, os, shutil, tarfile, zipfile, gzip
P=Path(__file__).resolve().parents[2]
O=P/'output/hp200lx-release4.0'; A=O/'assets'; A.mkdir(parents=True,exist_ok=True)
D=O/'docs'; F=P/'output/hp200lx-39final2b'; S=F/'source'
CF=P/'output/hp200lx-release4-cf-c1'
sha=lambda b: hashlib.sha256(b).hexdigest()
def encode(v): return (json.dumps(v,indent=2)+'\n').encode()
def sums(files): return ''.join(sha(b)+'  '+n+'\n' for n,b in sorted(files.items())).encode()
def zipout(name, files):
 files=dict(files); files['SHA256SUMS.txt']=sums(files)
 with zipfile.ZipFile(A/name,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for n,b in sorted(files.items()):
   assert not n.startswith('/') and '..' not in Path(n).parts
   i=zipfile.ZipInfo(n,(2026,10,21,0,0,0)); i.compress_type=zipfile.ZIP_DEFLATED; i.external_attr=0o100644<<16
   z.writestr(i,b)
 with zipfile.ZipFile(A/name) as z:
  assert z.testzip() is None
  for n,b in files.items(): assert z.read(n)==b,n
 print(name, (A/name).stat().st_size,flush=True)
 return files
bootmeta=json.loads((F/'dist/VALIDATION.json').read_text())
with zipfile.ZipFile(F/'dist/hp200lx-3.9-final2b-boot.zip') as z:
 boot={n:z.read(n) for n in bootmeta['boot_files']}
 for n,b in boot.items():
  assert sha(b)==bootmeta['boot_files'][n]['sha256']
  assert len(b)==bootmeta['boot_files'][n]['bytes']
license=(S/'src/LICENSE').read_bytes()
install=b'''HP 200LX package 4.0 - ELKS 0.9.2\n\nCopy ONLY the ELKS39FB folder to C:\\ELKS39FB. Keep all 11 files together.\nAllow 320 KiB free C: space for boot files and generated KERNBOP.\nFINAL2b binaries are promoted unchanged; their 3.9-final2b version is expected.\n\nFrom a plain DOS prompt, exit System Manager first:\nC:\nCD \\ELKS39FB\nRUNELKS /CF\n\nAdd /DS on double-speed units. CF sleep needs no /SLEEPTEST.\nLocal empty slot: RUNELKS /LOCAL C:\\ELKS2M.MNX /NONET /SLEEPTEST\nLocal Accton: RUNELKS /LOCAL C:\\ELKS4M.MNX /SLEEPNIC\nAdd /DS where appropriate. Local sleep requires the idle initial shell.\nClose serial and graphics/apps first. /SLEEPNIC retains idle ktcp.\nWithout either local sleep flag, local suspend remains disabled.\n\nDownload a CF image or local MNX separately. Never write an MNX as a whole disk.\nThe 4.0 README and release guides are authoritative over historical image text:\nhttps://github.com/l00nix/elks-on-hp200lx/releases/tag/hp200lx-release-4.0\n'''
zipout('hp200lx-4.0-boot.zip',{**boot,'README.txt':install,'LICENSE.txt':license,
 'BOOT-MANIFEST.json':encode(bootmeta['boot_files']),
 'docs/SLEEP.md':(D/'README.md').read_text().split('### Sleep modes\n',1)[1].split('## Choose your filesystem',1)[0].encode(),
 'docs/ACCEPTANCE-4.0.md':(D/'ACCEPTANCE-4.0.md').read_bytes()})
local={}
for profile,rec in zip(['2mb','4mb'],bootmeta['filesystem_images'][1:]):
 b=(P/'output/elx-inject-0.1'/profile/rec['name']).read_bytes(); assert sha(b)==rec['sha256']; local[rec['name']]=b
zipout('hp200lx-4.0-local-images.zip',{**local,'LICENSE.txt':license,'README.txt':install+b'\nLocal images are byte-preserved; use the ELX tools update pack for newer utilities.\n',
 'ELX-TOOLS.md':(D/'ELX-TOOLS-4.0.md').read_bytes(),
 'SOURCE.txt':b'Upstream ELKS v0.9.2 plus ELX injector payload. Sources in the matching 4.0 source and image-tools packages. https://github.com/ghaerr/elks/tree/v0.9.2\n'})
cfmeta=json.loads((CF/'REPORT.json').read_text())
for size,r in cfmeta['images'].items():
 b=(CF/r['image']).read_bytes(); assert len(b)==r['image_bytes'] and sha(b)==r['sha256']
 zipout(f'hp200lx-4.0-cf-{size}mb.zip',{r['image']:b,'README.txt':install+b'\nWrite IMG to whole CF card; this replaces its contents. Check minimum card capacity.\n',
 'CF-IMAGES.md':(D/'CF-IMAGES-4.0.md').read_bytes(),'ELX-TOOLS.md':(D/'ELX-TOOLS-4.0.md').read_bytes(),'LICENSE.txt':license})
appmeta=json.loads((S/'BASE-FINAL2-VALIDATION.json').read_text())['applications']
apps={}
for n,r in appmeta.items():
 b=(S/r['path']).read_bytes(); assert sha(b)==r['sha256']; apps[n]=b
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as t:
 for n,b in {**apps,'README.txt':(D/'ELX-TOOLS-4.0.md').read_bytes(),'LICENSE.txt':license}.items():
  i=tarfile.TarInfo('elx40/'+n); i.size=len(b); i.mode=0o755 if n in apps else 0o644; i.mtime=1792540800; t.addfile(i,io.BytesIO(b))
appfiles={'bin/'+n:b for n,b in apps.items()}
appfiles.update({'ELX40.TAR':buf.getvalue(),'README.md':(D/'ELX-TOOLS-4.0.md').read_bytes(),'LICENSE.txt':license})
for n in ['meminfo','ps']: appfiles['compat/'+n]=(S/'compat'/n).read_bytes()
appfiles['compat/README.txt']=b'Optional ELKS meminfo/ps for older HP userlands. Stock v0.9.2 diagnostics do not need replacement. These are ELKS executables, not DOS.\n'
zipout('hp200lx-4.0-elx-tools.zip',appfiles)
# Sources include exact linked outputs needed by regression tests, but omit host cache/VCS.
source_name='hp200lx-4.0-source.tar.gz'
allowed_dirs={'src','applications','assets','build','compat','history','ports','tests','vendor'}
allowed_files={'assemble-final1.sh','assemble-final2.sh','verify-preserved.py','BASE-FINAL2-VALIDATION.json','BASE-FINAL2a-VALIDATION.json','NETWORK-BASELINE.json'}
sourcehash={}
def addbytes(t,name,b,mode=0o644):
 i=tarfile.TarInfo('hp200lx-4.0-source/'+name); i.size=len(b); i.mode=mode; i.mtime=1792540800; t.addfile(i,io.BytesIO(b))
with (A/source_name).open('wb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as g:
  with tarfile.open(fileobj=g,mode='w|',format=tarfile.PAX_FORMAT) as t:
   for p in sorted(S.rglob('*')):
    r=p.relative_to(S)
    if any(x in {'.git','__pycache__','.DS_Store','.env','cross'} for x in r.parts) or p.suffix=='.pyc': continue
    if r.parts[0] not in allowed_dirs and str(r) not in allowed_files and not p.name.startswith('CHANGES-'): continue
    if p.is_symlink():
     target=os.readlink(p)
     if os.path.isabs(target): continue
     i=tarfile.TarInfo('hp200lx-4.0-source/'+str(r)); i.type=tarfile.SYMTYPE; i.linkname=target; i.mode=0o777; i.mtime=1792540800; t.addfile(i)
    elif p.is_file():
     b=p.read_bytes(); sourcehash[str(r)]=sha(b); addbytes(t,str(r),b,p.stat().st_mode&0o777)
   for name,b in {'README.md':(D/'BUILD-4.0.md').read_bytes(),'SOURCE-HISTORY.md':(S/'SOURCE.md').read_bytes(),'RELEASE-4.0.md':(D/'RELEASE-4.0.md').read_bytes(),'ACCEPTANCE-4.0.md':(D/'ACCEPTANCE-4.0.md').read_bytes(),'FINAL2b-SOFTWARE-VALIDATION.json':(F/'dist/VALIDATION.json').read_bytes(),'SOURCE-SHA256.json':encode(sourcehash)}.items(): addbytes(t,name,b)
print(source_name,(A/source_name).stat().st_size,flush=True)
# Retain the historically pinned injector inputs and matching payload sources.
imagefiles={
 'README.txt':b'''Release 4.0 image construction tools\n\nHistorical candidate reports and READMEs retain their original versions.\nUse the published 4.0 README for current boot commands and support scope.\nThe injector archive reconstructs the unchanged local images; it retains their\nolder ELX payloads. The CF build-input archive reconstructs the unchanged CF images.\nThese tools do not update kernels. Always use the separate 4.0 boot ZIP.\n\nOffline growth: keep grow_cf.py and minix.py together, then run:\npython3 grow_cf.py used-card.img grown-card.img --card-mb 64\nNever use a live root or block device as input. See CF-IMAGES.md.\n''',
 'CF-IMAGES.md':(D/'CF-IMAGES-4.0.md').read_bytes(),
 'grow_cf.py':(CF/'grow_cf.py').read_bytes(),'minix.py':(CF/'minix.py').read_bytes(),
 'COPYING':license,
 'cf-build-inputs.zip':(CF/'hp200lx-r4-c1-build-inputs.zip').read_bytes(),
 'ELX-injector-0.1.zip':(P/'output/elx-inject-0.1/dist/ELX-injector-0.1.zip').read_bytes(),
 'ELX-payload-sources-0.1.zip':(P/'output/elx-inject-0.1/dist/ELX-payload-sources-0.1.zip').read_bytes(),
 'cf-validation.json':(CF/'VALIDATION.json').read_bytes(),
 'local-validation.json':(P/'output/elx-inject-0.1/VALIDATION.json').read_bytes()
}
zipout('hp200lx-4.0-image-tools.zip',imagefiles)
manifest={'package':'HP 200LX 4.0','upstream':'ELKS 0.9.2','promoted_build':'3.9 FINAL2b','date':'2026-10-21','acceptance':'Maintainer closed hardware acceptance including sleep guards on 2026-10-21','binaries_rebuilt':False,'filesystem_bytes_changed':False,'boot_folder':'ELKS39FB','boot_files':bootmeta['boot_files'],'software_checks':bootmeta['software_tests'],'local_images':bootmeta['filesystem_images'][1:],'cf_images':{k:{q:v for q,v in r.items() if q!='hardware_tested'} for k,r in cfmeta['images'].items()},'utilities':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in apps.items()},'assets':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(A.iterdir()) if p.suffix in ('.zip','.gz')}}
(A/'MANIFEST.json').write_bytes(encode(manifest))
(A/'SHA256SUMS.txt').write_bytes(sums({p.name:p.read_bytes() for p in A.iterdir() if p.name!='SHA256SUMS.txt'}))
(O/'SOURCE-SHA256.json').write_bytes(encode(sourcehash))
print('All frozen identities and ZIP contents verified.',flush=True)

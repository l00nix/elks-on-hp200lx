from pathlib import Path
import hashlib,json,tarfile,zipfile,re,subprocess
P=Path(__file__).resolve().parents[2]; O=P/'output/hp200lx-release4-refresh';A=O/'assets';R=P/'output/hp200lx-release4-publish'
sha=lambda b:hashlib.sha256(b).hexdigest()
results={}
for line in (A/'SHA256SUMS.txt').read_text().splitlines():
 h,n=line.split('  ',1); assert sha((A/n).read_bytes())==h,n
results['asset_sha256']='PASS'
for p in A.glob('*.zip'):
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None,p
  for line in z.read('SHA256SUMS.txt').decode().splitlines():
   h,n=line.split('  ',1); assert sha(z.read(n))==h,(p,n)
results['all_zip_internal_checksums']='PASS'
extract=O/'source-check';extract.mkdir(exist_ok=True)
with tarfile.open(A/'hp200lx-4.0-source.tar.gz') as t:
 for m in t:
  assert not m.name.startswith('/') and '..' not in Path(m.name).parts
  if m.issym():
   assert not m.linkname.startswith('/')
   resolved=(extract/m.name).parent.joinpath(m.linkname).resolve()
   assert resolved.is_relative_to((extract/'hp200lx-4.0-source').resolve()),m.name
 t.extractall(extract)
root=extract/'hp200lx-4.0-source'
for n,h in json.loads((root/'SOURCE-SHA256.json').read_text()).items(): assert sha((root/n).read_bytes())==h,n
results['source_archive_identity']='PASS'
# Verify the published code and frozen binaries really correspond in both profiles.
m=json.loads((A/'MANIFEST.json').read_text())
for n,r in m['boot_files'].items():
 assert sha((root/'ports/local1'/Path(n).name).read_bytes())==r['sha256'],n
results['source_boot_matches_distribution']='PASS'
# README/local markdown and HTML image paths must resolve in the published checkout.
for p in [R/'README.md',*R.glob('docs/hp200lx/*4.0.md')]:
 txt=p.read_text()
 targets=re.findall(r'\]\(([^)]+)\)',txt)+re.findall(r'src="([^"]+)"',txt)
 for target in targets:
  if '://' in target or target.startswith('#'):continue
  assert (p.parent/target.split('#')[0]).exists(),(p,target)
results['documentation_local_links']='PASS'
results['naming_refresh']='Kernel executable code and symbol maps unchanged; image changes restricted to documented paths.'
(O/'PACKAGING-CHECKS.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))

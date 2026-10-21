from pathlib import Path
import sys,struct,subprocess,tempfile,json,stat
P=Path(__file__).resolve().parents[2];O=P/'output/hp200lx-release4-refresh';S=O/'source';D=O/'images';D.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'tools/elx-inject'));from minix import Minix,sha
mfs=O/'mfs';v=P/'tools/elx-inject/vendor/mfs'
if not mfs.exists():subprocess.run(['cc','-O2','-o',str(mfs)]+[str(v/(n+'.c')) for n in 'mkfs genfs dir iname inode main reader super utils writer getoptx'.split()],check=True)
results={}
for label,path,outname in [('local2',P/'output/elx-inject-0.1/2mb/ELKS2M.MNX','ELKS2M.MNX'),('local4',P/'output/elx-inject-0.1/4mb/ELKS4M.MNX','ELKS4M.MNX')]+[(f'cf{n}',P/f'output/hp200lx-release4-cf-c1/R4C1{n:02d}.IMG',f'ELKS4C{n:02d}.IMG') for n in [8,16,32,64]]:
 raw=path.read_bytes();start=0;length=len(raw)
 if label.startswith('cf'):sector,count=struct.unpack_from('<II',raw,454);start=sector*512;length=count//2*1024
 before=Minix(raw[start:start+length]).records();updates={}
 if label.startswith('local'):
  updates['/etc/issue']=b'ELKS on HP 200LX - package 4.0 / ELKS 0.9.2\n'
  updates['/root/ELX.txt']=('HP 200LX package 4.0 - '+label+' filesystem\nCopy the complete boot folder to C:\\ELKS4.\nRUNELKS /LOCAL C:\\'+outname+' /NONET\nAdd /DS for double speed. Empty-slot local sleep: add /SLEEPTEST.\nFor Accton networking, omit /NONET; add /SLEEPNIC for idle-network sleep.\nLocal sleep requires the idle initial shell; edit and graphics block sleep.\nUse the separate ELX update pack for the newest utilities.\nSerial: sh /root/ser (9600 8N1); exit from the peer before sleep.\nSee the 4.0 release README for usage and limitations.\n').encode()
 else:
  updates['/linux']=(S/'ports/local1/KERNCF').read_bytes()
  updates['/etc/issue']=b'ELKS on HP 200LX - package 4.0 / ELKS 0.9.2\nCF root; kernel loaded from C:\\ELKS4\n'
  updates['/root/RELEASE.TXT']=b'HP 200LX package 4.0\nUse the complete 4.0 boot folder C:\\ELKS4. RUNELKS /CF; add /DS for double speed.\nGuarded CF sleep requires no /SLEEPTEST.\nImages have 2048 inodes and support offline host growth through the 64 MB profile.\nNo first-boot or online resizer. See release documentation.\n'
  d=before['/root/HOWTO.TXT']['data'].decode();d=d.replace('Release 4 CF candidate 1','Release 4.0').replace('unchanged 3.9 FINAL','4.0').replace('ELKS39F','ELKS4').replace('3.9 FINAL','4.0');updates['/root/HOWTO.TXT']=d.encode()
  updates['/bootopts']=before['/bootopts']['data'].replace(b'Release 4 CF candidate',b'Release 4.0 CF')
 with tempfile.TemporaryDirectory(dir=O) as tmp:
  tmp=Path(tmp);fs=tmp/'fs';fs.write_bytes(raw[start:start+length]);src=tmp/'file'
  for name,data in updates.items():
   src.write_bytes(data);src.chmod(before[name]['mode']&0o777)
   r=subprocess.run([str(mfs),str(fs),'cp',str(src),name],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
  afterbytes=fs.read_bytes();after=Minix(afterbytes).records();assert before.keys()==after.keys()
  for name,r in before.items():
   expected=updates.get(name,r.get('data'))
   assert after[name].get('data')==expected,name
   for k in ['mode','uid','gid','device','links']:assert r.get(k)==after[name].get(k),(name,k)
   if name not in updates:
    assert {k:v for k,v in r.items() if k!='data'}=={k:v for k,v in after[name].items() if k!='data'},name
  final=raw[:start]+afterbytes+raw[start+length:];assert len(final)==len(raw)
  (D/outname).write_bytes(final)
 results[outname]={'bytes':len(final),'sha256':sha(final),'original_sha256':sha(raw),'changed_paths':list(updates),'all_other_paths_and_metadata_unchanged':True,'free_bytes':Minix(afterbytes).free_bytes()}
(O/'IMAGE-CHANGES.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))

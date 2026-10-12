# Convert a single/multi-region .litematic to a Sponge Schematic v3 (.schem)
import sys, numpy as np, nbtlib
from nbtlib import Compound, Int, Short, String, IntArray, ByteArray, List
def state_str(e):
    s=str(e['Name'])
    if 'Properties' in e and len(e['Properties']):
        s+='['+','.join(f'{k}={v}' for k,v in sorted(e['Properties'].items()))+']'
    return s
def decode(r):
    sx,sy,sz=(abs(int(r['Size'][k])) for k in 'xyz')
    pal=[state_str(e) for e in r['BlockStatePalette']]
    bits=max(2,int(np.ceil(np.log2(len(pal)))))
    longs=np.array(r['BlockStates'],dtype=np.int64).view(np.uint64)
    n=sx*sy*sz; idx=np.arange(n,dtype=np.uint64)*np.uint64(bits)
    li=(idx>>np.uint64(6)).astype(np.int64); bo=idx&np.uint64(63)
    mask=np.uint64((1<<bits)-1)
    v=(longs[li]>>bo)
    span=(bo+np.uint64(bits))>np.uint64(64)
    nxt=np.where(span,longs[np.minimum(li+1,len(longs)-1)],np.uint64(0))
    sh=np.where(span,np.uint64(64)-bo,np.uint64(0))
    v=np.where(span,v|(nxt<<sh),v)&mask
    return pal,v.astype(np.int32).reshape(sy,sz,sx),sx,sy,sz  # [y][z][x]
src,dst=sys.argv[1],sys.argv[2]
n=nbtlib.load(src); dv=int(n['MinecraftDataVersion'])
regs=list(n['Regions'].items())
# region origins (handle negative sizes)
boxes=[]
for name,r in regs:
    p=[int(r['Position'][k]) for k in 'xyz']; s=[int(r['Size'][k]) for k in 'xyz']
    lo=[p[i]+min(0,s[i]+1) for i in range(3)]; boxes.append(lo)
mn=np.min(boxes,0)
W=H=L=0; vols=[]
for (name,r),lo in zip(regs,boxes):
    pal,a,sx,sy,sz=decode(r); o=np.array(lo)-mn
    vols.append((pal,a,o)); W=max(W,o[0]+sx); H=max(H,o[1]+sy); L=max(L,o[2]+sz)
gpal={'minecraft:air':0}; V=np.zeros((H,L,W),np.int32)
for pal,a,o in vols:
    remap=np.array([gpal.setdefault(s,len(gpal)) for s in pal],np.int32)
    m=a!=0 if pal[0]=='minecraft:air' else np.ones(a.shape,bool)
    sub=V[o[1]:o[1]+a.shape[0],o[2]:o[2]+a.shape[1],o[0]:o[0]+a.shape[2]]
    sub[m]=remap[a][m]
flat=V.reshape(-1)  # x + z*W + y*W*L
two=flat>=128
out=bytearray()
fb=flat.astype(np.int64)
# generic varint encoding
parts=[]
rem=fb.copy(); bytes_=[]
while True:
    b=(rem&127).astype(np.uint8); rem>>=7
    more=rem>0
    bytes_.append(np.where(more,b|128,b).astype(np.uint8)); 
    if not more.any(): break
cnt=np.ones(len(fb),np.int64)
r2=fb>>7
while (r2>0).any(): cnt+=r2>0; r2>>=7
data=np.empty(int(cnt.sum()),np.uint8); pos=np.concatenate([[0],np.cumsum(cnt)[:-1]])
for k,bk in enumerate(bytes_):
    sel=cnt>k; data[pos[sel]+k]=bk[sel]
blocks=Compound({'Palette':Compound({s:Int(i) for s,i in gpal.items()}),'Data':ByteArray(data.view(np.int8)),'BlockEntities':List[Compound]([])})
md=n.get('Metadata',{})
sch=Compound({'Version':Int(3),'DataVersion':Int(dv),'Width':Short(W),'Height':Short(H),'Length':Short(L),
  'Offset':IntArray([0,0,0]),'Metadata':Compound({'Name':String(str(md.get('Name',''))),'Author':String(str(md.get('Author','')))}),'Blocks':blocks})
nbtlib.File({'Schematic':sch},gzipped=True).save(dst)
# verify by reading back
chk=nbtlib.load(dst)['Schematic']; d=np.array(chk['Blocks']['Data'],np.int8).view(np.uint8)
vals=[];i=0;res=np.empty(W*H*L,np.int64);k=0;cur=0;sh=0
dd=d.astype(np.int64); cont=(dd&128)>0
ends=np.nonzero(~cont)[0]; starts=np.concatenate([[0],ends[:-1]+1])
low=dd&127
dec=low[starts].copy()
for j in range(1,4):
    sel=starts+j<=ends; dec[sel]|=low[starts[sel]+j]<<(7*j)
inv={int(v):s for s,v in chk['Blocks']['Palette'].items()}
ok=(dec==flat).all()
print(dst,'size',W,H,L,'palette',len(gpal),'blocks',int((flat!=0).sum()),'DataVersion',dv,'verify',ok)

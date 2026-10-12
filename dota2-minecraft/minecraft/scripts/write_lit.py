import numpy as np, json, gzip, struct, time, sys
D='/home/user/dota_work/mc/'
import os; OD=os.environ.get('OD',D); B=np.load(OD+'B_final.npy'); pal=json.load(open(OD+'pal_final.json'))
bl={b['name']:b for b in json.load(open(D+'npm/mcd/package/minecraft-data/data/pc/1.21.11/blocks.json'))}
DEF={'axis':'y','snowy':'false','waterlogged':'false','powered':'false'}
entries=[]
for s in pal:
    n=s.split('[')[0].split(':')[1]; pr=dict(p.split('=') for p in s[s.index('[')+1:-1].split(',')) if '[' in s else {}
    st={x['name']:x for x in bl[n].get('states',[])}
    for k,t in st.items():
        if k not in pr: pr[k]=DEF.get(k, 'false' if t['type']=='bool' else str(t['values'][0]) if 'values' in t else '0')
    assert set(pr)==set(st),s
    entries.append(('minecraft:'+n,pr))
# merge duplicates
key=[n+str(sorted(p.items())) for n,p in entries]; uk={}; remap=np.zeros(len(pal),np.int32); final=[]
for i,k in enumerate(key):
    if k not in uk: uk[k]=len(final); final.append(entries[i])
    remap[i]=uk[k]
B=remap[B].astype(np.uint16)
# crop to used bounds
nz=np.nonzero(B.any((0,1)))[0]; B=B[:,:,:nz[-1]+1]
SX,SZ,SY=B.shape
print('size',SX,SY,SZ,'palette',len(final))
# NBT writer
def tag_str(s): b=s.encode(); return struct.pack('>H',len(b))+b
class W:
    def __init__(s): s.b=bytearray()
    def named(s,t,name): s.b+=bytes([t])+tag_str(name)
    def int(s,n,v): s.named(3,n); s.b+=struct.pack('>i',v)
    def long(s,n,v): s.named(4,n); s.b+=struct.pack('>q',v)
    def str(s,n,v): s.named(8,n); s.b+=tag_str(v)
    def comp(s,n): s.named(10,n)
    def end(s): s.b+=b'\0'
    def vec(s,n,x,y,z): s.comp(n); s.int('x',x); s.int('y',y); s.int('z',z); s.end()
    def emptylist(s,n): s.named(9,n); s.b+=bytes([0])+struct.pack('>i',0)
w=W(); w.comp('')
w.int('MinecraftDataVersion',4667); w.int('Version',6); w.int('SubVersion',1)
total=int((B>0).sum()); now=int(time.time()*1000)
w.comp('Metadata')
w.str('Name','Dota 2 Map'); w.str('Author','Claude'); w.str('Description','Dota 2 map recreated in Minecraft 1.21.11 (1.85 blocks per metre)')
w.int('RegionCount',1); w.long('TimeCreated',now); w.long('TimeModified',now)
w.int('TotalBlocks',total); w.int('TotalVolume',SX*SY*SZ); w.vec('EnclosingSize',SX,SY,SZ); w.end()
w.comp('Regions'); w.comp('Dota2')
w.vec('Position',0,0,0); w.vec('Size',SX,SY,SZ)
w.named(9,'BlockStatePalette'); w.b+=bytes([10])+struct.pack('>i',len(final))
for n,pr in final:
    w.str('Name',n)
    if pr:
        w.comp('Properties')
        for k,v in sorted(pr.items()): w.str(k,v)
        w.end()
    w.end()
bits=max(2,int(np.ceil(np.log2(len(final)))))
flat=B.transpose(2,1,0).reshape(-1).astype(np.uint64)  # index=(y*SZ+z)*SX+x
nl=(len(flat)*bits+63)//64
flat=np.pad(flat,(0,(-len(flat))%64))
parts=[]; CH=64*65536
for i in range(0,len(flat),CH):
    f=flat[i:i+CH]
    ba=((f[:,None]>>np.arange(bits,dtype=np.uint64))&1).astype(np.uint8).reshape(-1)
    parts.append(np.packbits(ba,bitorder='little').view('<u8').astype('>u8'))
longs=np.concatenate(parts)[:nl].astype('>u8')
w.named(12,'BlockStates'); w.b+=struct.pack('>i',nl)+longs.tobytes()
for n in ('TileEntities','Entities','PendingBlockTicks','PendingFluidTicks'): w.emptylist(n)
w.end(); w.end(); w.end()
out=D+'out/dota2_map.litematic'
with gzip.open(out,'wb',compresslevel=9) as f: f.write(bytes(w.b))
json.dump({'size':[SX,SY,SZ],'bits':bits,'palette':[n+('['+','.join(f'{k}={v}' for k,v in sorted(p.items()))+']' if p else '') for n,p in final]},open(D+'out/lit_info.json','w'))
print('wrote',out,'blocks',total)

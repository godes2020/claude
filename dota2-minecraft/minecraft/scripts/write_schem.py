# Sponge Schematic v3 (.schem) for WorldEdit / FAWE, Minecraft 1.21.11
import numpy as np, json, gzip, struct, time
D='/home/user/dota_work/mc/'
import os; OD=os.environ.get('OD',D); B=np.load(OD+'B_final.npy'); pal=json.load(open(OD+'pal_final.json'))
bl={b['name']:b for b in json.load(open(D+'npm/mcd/package/minecraft-data/data/pc/1.21.11/blocks.json'))}
DEF={'axis':'y','snowy':'false','waterlogged':'false','powered':'false'}
keys=[]
for s in pal:
    n=s.split('[')[0].split(':')[1]; pr=dict(p.split('=') for p in s[s.index('[')+1:-1].split(',')) if '[' in s else {}
    st={x['name']:x for x in bl[n].get('states',[])}
    for k,t in st.items():
        if k not in pr: pr[k]=DEF.get(k,'false' if t['type']=='bool' else str(t['values'][0]) if 'values' in t else '0')
    assert set(pr)==set(st),s
    keys.append('minecraft:'+n+('['+','.join(f'{k}={v}' for k,v in sorted(pr.items()))+']' if pr else ''))
uk={}; remap=np.zeros(len(pal),np.int32)
for i,k in enumerate(keys):
    if k not in uk: uk[k]=len(uk)
    remap[i]=uk[k]
B=remap[B].astype(np.uint16)
nz=np.nonzero(B.any((0,1)))[0]; B=B[:,:,:nz[-1]+1]
W,L,H=B.shape  # x, z, y
flat=B.transpose(2,1,0).reshape(-1).astype(np.int32)  # index = x + z*W + y*W*L
assert flat.max()<16384
two=flat>=128
out=np.empty(len(flat)+int(two.sum()),np.uint8)
pos=np.arange(len(flat))+np.concatenate([[0],np.cumsum(two)[:-1]])
out[pos]=np.where(two,(flat&127)|128,flat).astype(np.uint8)
out[pos[two]+1]=(flat[two]>>7).astype(np.uint8)
def ts(s): b=s.encode(); return struct.pack('>H',len(b))+b
b=bytearray()
def named(t,n): b.extend(bytes([t])+ts(n))
b.extend(bytes([10])+ts(''))
named(10,'Schematic')
named(3,'Version'); b.extend(struct.pack('>i',3))
named(3,'DataVersion'); b.extend(struct.pack('>i',4667))
named(2,'Width'); b.extend(struct.pack('>H',W))
named(2,'Height'); b.extend(struct.pack('>H',H))
named(2,'Length'); b.extend(struct.pack('>H',L))
named(11,'Offset'); b.extend(struct.pack('>iiii',3,0,0,0))
named(10,'Metadata'); named(8,'Name'); b.extend(ts('Dota 2 Map')); named(8,'Author'); b.extend(ts('Claude'))
named(4,'Date'); b.extend(struct.pack('>q',int(time.time()*1000))); b.extend(b'\0')
named(10,'Blocks')
named(10,'Palette')
for k,v in uk.items(): named(3,k); b.extend(struct.pack('>i',v))
b.extend(b'\0')
named(7,'Data'); b.extend(struct.pack('>i',len(out))); b.extend(out.tobytes())
named(9,'BlockEntities'); b.extend(bytes([10])+struct.pack('>i',0))
b.extend(b'\0')  # Blocks
b.extend(b'\0')  # Schematic
b.extend(b'\0')  # root
with gzip.open(D+'out/dota2_map.schem','wb',compresslevel=9) as f: f.write(bytes(b))
print('size',W,H,L,'palette',len(uk),'bytes',len(out))

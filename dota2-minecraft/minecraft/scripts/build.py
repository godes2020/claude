import numpy as np, json, time
from scipy import ndimage as ndi
import os
T=time.time(); D='/home/user/dota_work/mc/'; OD=os.environ['OD']
G=json.load(open(OD+'grid.json')); S,XMAX,YMAX=G['S'],G['XMAX'],G['YMAX']
meta=json.load(open(D+'meta.json')); MN=[m['name'].lower() for m in meta['mats']]
PAL=json.load(open(D+'palette.json'))
CAT=np.load(OD+'CAT.npy',mmap_mode='r'); COL=np.load(OD+'COL.npy',mmap_mode='r'); MAT=np.load(OD+'MAT.npy',mmap_mode='r')
NX,NZ,NY=CAT.shape
F=S/1.85
rng=np.random.default_rng(7)
B=np.zeros((NX,NZ,NY),np.uint16)
pal=['minecraft:air']; pid={'minecraft:air':0}
def P(name,**pr):
    s='minecraft:'+name+('['+','.join(f'{k}={str(v).lower()}' for k,v in sorted(pr.items()))+']' if pr else '')
    if s not in pid: pid[s]=len(pal); pal.append(s)
    return pid[s]
AXIS={'basalt','polished_basalt','oak_log','spruce_log','dark_oak_log','pale_oak_log','cherry_log','birch_log','mangrove_log','jungle_log','stripped_oak_log','bamboo_block','bone_block','oak_wood','spruce_wood','dark_oak_wood','pale_oak_wood','cherry_wood','birch_wood','mangrove_wood','acacia_log','muddy_mangrove_roots'}
LEAFB={'oak_leaves','dark_oak_leaves','spruce_leaves','birch_leaves','jungle_leaves','azalea_leaves','flowering_azalea_leaves','cherry_leaves','pale_oak_leaves','mangrove_leaves','acacia_leaves'}
def BP(name):
    if name in AXIS: return P(name,axis='y')
    if name in LEAFB: return P(name,distance=7,persistent='true',waterlogged='false')
    return P(name)
def lum(c): return c[...,0]*0.3+c[...,1]*0.59+c[...,2]*0.11
def nearest(cols,names,src,pen=None,gain=1.0,noise=0.0):
    pc=np.array([PAL[src][n] for n in names],np.float32)
    c=cols.astype(np.float32)*gain
    if noise>0: c=c+rng.normal(0,noise,cols.shape).astype(np.float32)
    out=np.empty(len(c),np.int32); pn=np.zeros(len(names),np.float32) if pen is None else np.array([pen.get(n,0) for n in names],np.float32)
    for i in range(0,len(c),500000):
        cc=c[i:i+500000]; rm=(cc[:,None,0]+pc[None,:,0])/2
        dr=cc[:,None,0]-pc[None,:,0]; dg=cc[:,None,1]-pc[None,:,1]; db=cc[:,None,2]-pc[None,:,2]
        d=np.sqrt((2+rm/256)*dr*dr+4*dg*dg+(2+(255-rm)/256)*db*db)+pn
        out[i:i+500000]=d.argmin(1)
    return out
def autogain(cols,target):
    l=np.median(lum(cols.astype(np.float32))); return float(np.clip(lum(np.array(target,np.float32))/max(l,1),0.6,2.5))
def snoise(x,z,y,cell,seed):
    r=np.random.default_rng(seed); g=r.random((NX//cell+3,NZ//cell+3,NY//max(cell//2,1)+3)).astype(np.float32)
    g=ndi.gaussian_filter(g,0.8)
    g=(g-g.mean())/g.std()
    return ndi.map_coordinates(g,[x/cell,z/cell,y/max(cell//2,1)],order=1,mode='nearest')
def snoise2(cell,seed):
    r=np.random.default_rng(seed); g=r.random((NX//cell+3,NZ//cell+3)).astype(np.float32)
    g=ndi.gaussian_filter(g,0.8); g=(g-g.mean())/g.std()
    return ndi.zoom(g,cell,order=1)[:NX,:NZ]
def modefilt(lab,mask,size,passes=2):
    lab=lab.copy()
    for _ in range(passes):
        cl=np.unique(lab[mask]); best=np.full(lab.shape,-1.0,np.float32); out=lab.copy()
        for c in cl:
            cnt=ndi.uniform_filter(((lab==c)&mask).astype(np.float32),size)
            u=mask&(cnt>best); out[u]=c; best[u]=cnt[u]
        lab=np.where(mask,out,lab)
    return lab
ii,jj=np.indices((NX,NZ))
xw=XMAX-(jj+0.5)/S; yw=YMAX-(ii+0.5)/S
side=(xw-yw)+ndi.gaussian_filter(rng.normal(0,25,(NX,NZ)),6)
DIRE=side>0
print('load',time.time()-T,flush=True)
# ---------------- ground ----------------
g=(CAT==4)|(CAT==5)
has=g.any(2); gtop=(NY-1-np.argmax(g[:,:,::-1],axis=2)).astype(np.int32); gtop[~has]=-1
inside=ndi.binary_fill_holes(ndi.binary_closing(has,iterations=int(4*F)))
di,(ni,nj)=ndi.distance_transform_edt(~has,return_indices=True)
miss=inside&~has
gtop[miss]=gtop[ni[miss],nj[miss]]
tcol=COL[ii,jj,np.maximum(gtop,0)].copy(); tcol[miss]=tcol[ni[miss],nj[miss]]
tlava=(CAT[ii,jj,np.maximum(gtop,0)]==5)&inside
tmat=MAT[ii,jj,np.maximum(gtop,0)]
L=np.load(OD+'L_decal.npz'); Hd,Cd=L['H'],L['C']
path=inside&(Hd>=gtop-1.5)&(Hd<=gtop+3)
tcol[path]=Cd[path]
tcol=np.stack([ndi.gaussian_filter(tcol[...,c].astype(np.float32),1.5*F) for c in range(3)],-1)
Lw=np.load(OD+'L_water.npz'); Hw=Lw['H']
wl=np.floor(Hw-0.3).astype(np.int32); wl[Hw<0]=-1
water=inside&(Hw>=0)&(Hw-gtop>=0.3)&(Hw-gtop<=8)
water=ndi.binary_opening(water,iterations=1)
wd=ndi.distance_transform_edt(water)
extra=(wd>=4*F).astype(np.int32)+(wd>=9*F)+(wd>=14*F)
surf=np.maximum(np.floor(Hw-0.3).astype(np.int32),gtop)
bed=surf-1  # water exactly one block deep everywhere
wl=np.where(water,surf,-1)
# smooth isolated 1-voxel spikes/pits in gtop
med=ndi.median_filter(gtop,3)
sp=inside&~water&(np.abs(gtop-med)>=2)&(ndi.maximum_filter(gtop,3)-ndi.minimum_filter(gtop,3)<=3)
gtop[sp]=med[sp]
gtop[water]=bed[water]
print('ground cols',inside.sum(),'water',water.sum(),'path',path.sum(),'lava',tlava.sum(),time.time()-T,flush=True)
RAD_TOP=['grass_block','moss_block','podzol','coarse_dirt','gravel','stone','andesite','cobblestone','mossy_cobblestone']
RAD_PEN={'grass_block':-30,'moss_block':-5,'stone':10,'andesite':10,'cobblestone':15}
DIRE_TOP=['coarse_dirt','rooted_dirt','gravel','packed_mud','tuff','blackstone','cobbled_deepslate','soul_soil','podzol','andesite']
DIRE_PEN={'coarse_dirt':-6,'gravel':-4,'tuff':-3,'rooted_dirt':-3,'packed_mud':-5,'soul_soil':-3}
PATH=['coarse_dirt','packed_mud','gravel','stone_bricks','cobblestone','polished_andesite','mossy_stone_bricks','polished_blackstone_bricks']
PATH_PEN={'coarse_dirt':-15,'gravel':-5,'packed_mud':-5}
BED=['mud','clay','gravel','sand','dirt']
topname=np.empty((NX,NZ),object); topname[:]=''
def assign(mask,names,pen,gain):
    sel=np.nonzero(mask)
    k=nearest(tcol[sel],names,'ground',pen,gain)
    topname[sel]=np.array(names,object)[k]
mR=inside&~DIRE&~path&~water&~tlava; mD=inside&DIRE&~path&~water&~tlava
assign(mR,RAD_TOP,RAD_PEN,autogain(tcol[mR],PAL['ground']['grass_block']))
assign(mD,DIRE_TOP,DIRE_PEN,autogain(tcol[mD],PAL['ground']['coarse_dirt']))
mP=inside&path&~water&~tlava
if mP.any(): assign(mP,PATH,PATH_PEN,autogain(tcol[mP],PAL['ground']['dirt_path']))
mW=inside&water&~tlava
assign(mW,BED,{'mud':-5,'gravel':-5},autogain(tcol[mW],PAL['ground']['mud'])*1.1)
topname[inside&tlava]='magma_block'
# majority filter -> coherent patches, no speckle
TN=sorted(set(topname[inside]))
lab=np.full((NX,NZ),-1,np.int32); lab[inside]=np.searchsorted(TN,topname[inside].astype(str))
for msk in (mR,mD,mP,mW):
    lab=modefilt(lab,msk,int(5*F)|1)
topname[inside]=np.array(TN,object)[lab[inside]]
print('top classes',{n:int((topname==n).sum()) for n in TN},flush=True)
print('top assigned',time.time()-T,flush=True)
# sides/interior: per column fill from gfloor..gtop-1
gt=np.where(inside,gtop,-1)
nmin=ndi.minimum_filter(np.where(inside,gt,0),3)
gfloor=np.clip(np.minimum(nmin,gt)-3,0,None)
yy=np.arange(NY,dtype=np.int16)[None,None,:]
below=(yy>=gfloor[:,:,None])&(yy<gt[:,:,None])
# only voxels visible (exposed horizontally) need colour-matched blocks
sel=np.nonzero(below)
print('fill voxels',len(sel[0]),time.time()-T,flush=True)
expo=np.zeros(len(sel[0]),bool)
for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
    a=np.clip(sel[0]+dx,0,NX-1); b=np.clip(sel[1]+dz,0,NZ-1)
    expo|=gt[a,b]<sel[2]
cc=np.zeros((len(sel[0]),3),np.uint8); found=np.zeros(len(sel[0]),bool)
ex=np.nonzero(expo)[0]
for k in [0,1,-1,2,-2,3,-3,4,-4,6,-6,8,-8]:
    if len(ex)==0: break
    yk=np.clip(sel[2][ex]+k,0,NY-1); ok=CAT[sel[0][ex],sel[1][ex],yk]==4
    cc[ex[ok]]=COL[sel[0][ex[ok]],sel[1][ex[ok]],yk[ok]]; ex=ex[~ok]
cc[ex]=128
dirt_like=np.isin(topname[sel[0],sel[1]],['grass_block','moss_block','podzol','rooted_dirt','dirt'])
depth=gt[sel[0],sel[1]]-sel[2]
names=np.empty(len(sel[0]),object)
dmask=DIRE[sel[0],sel[1]]
names[:]=np.where(dmask,'deepslate','stone')
names[dirt_like&(depth<=3)]='dirt'
n1=snoise(sel[0],sel[1],sel[2],int(14*F),11); n2=snoise(sel[0],sel[1],sel[2],int(8*F),12)
dk=lum(cc.astype(np.float32))<95
rockR=np.where(n1<-0.5,'andesite',np.where(n1>0.7,'tuff','stone'))
rockR=np.where((n2>0.9)&~(n1>0.7),'cobblestone',rockR)
rockD=np.where(n1<-0.3,'deepslate',np.where(n1>0.6,'cobbled_deepslate','tuff'))
rockD=np.where(dk&(n2>0.5),'blackstone',rockD)
rk=np.where(dmask,rockD,rockR)
m=expo&~(dirt_like&(depth<=2))
names[m]=rk[m]
names[expo&dirt_like&(depth<=2)&~dmask&(n2>0.6)]='mossy_cobblestone'
edge=~ndi.binary_erosion(inside,iterations=int(2*F))
em=edge[sel[0],sel[1]]
names[em]=np.where(n1[em]<0,'deepslate','tuff')
un,inv=np.unique(names,return_inverse=True)
B[sel]=np.array([BP(n) for n in un],np.uint16)[inv]
tsel=np.nonzero(inside)
un,inv=np.unique(topname[tsel],return_inverse=True)
B[tsel[0],tsel[1],gt[tsel]]=np.array([BP(n) for n in un],np.uint16)[inv]
del below
print('ground placed',time.time()-T,flush=True)
# ---------------- water ----------------
wsel=np.nonzero(water)
WB=P('water',level=0)
for k in range(1,40):
    m=wl[wsel]>=gt[wsel]+k
    if not m.any(): break
    B[wsel[0][m],wsel[1][m],gt[wsel][m]+k]=WB
wdepth=np.where(water,wl-gt,0)
print('water placed',time.time()-T,flush=True)
np.savez(OD+'stage_ground.npz',gt=gt,inside=inside,water=water,wl=wl,DIRE=DIRE,path=path)
# ---------------- buildings ----------------
bm=(CAT==8)
bs=np.nonzero(bm)
bmat=MAT[bs]; bcol=COL[bs]
mname=np.array(MN+[''],object)[bmat]
def mstarts(prefixes): return np.array([any(n.startswith(p) for p in prefixes) for n in MN]+[False])[bmat]
GEN=[n for n in PAL['build'] if not n.endswith('_wool') and n not in ('oak_log','spruce_log','dark_oak_log','stripped_oak_log','shroomlight','nether_wart_block','sea_lantern','blue_ice','lapis_block','magma_block','crying_obsidian','tuff_bricks2','amethyst_block','gold_block','iron_block','moss_block')]
bn=np.empty(len(bs[0]),object)
BPEN={'stone_bricks':-8,'mossy_stone_bricks':-4,'polished_andesite':-3,'cobblestone':-3}
GAIN=autogain(bcol,PAL['build']['stone_bricks'])
bn[:]=''
LISTS={}
special=[
 (('team_banner_radiant','bannerbase_radiant','team_logo_radiant'),['green_wool','lime_wool','white_wool','yellow_wool','gold_block','oak_planks','spruce_planks','stone_bricks']),
 (('team_banner_dire','bannerbase_dire','team_logo_dire'),['red_wool','black_wool','brown_wool','orange_wool','nether_bricks','red_nether_bricks','polished_blackstone','dark_oak_planks']),
 (('crystal',),['amethyst_block','blue_ice','light_blue_wool','prismarine','sea_lantern']),
 (('aegis','gold','radiant_ancient001'),['gold_block','raw_gold_block','white_wool','calcite','quartz_block','light_blue_terracotta','prismarine']),
 (('leanto_fur',),['brown_wool','white_wool','black_wool']),
 (('lava','cracks'),['magma_block','blackstone','obsidian']),
 (('log002','leanto_sticks','bad_sticks','wood_fence','wood_walls','water_creep_camp_huts','water_creep_camp_fish','neutral_stash'),['oak_planks','spruce_planks','dark_oak_planks','pale_oak_planks','jungle_planks','mangrove_planks','birch_planks','oak_log','spruce_log','dark_oak_log','stripped_oak_log','bamboo_planks']),
]
mlist=np.zeros(len(MN)+1,np.int32)  # 0=GEN
SPL=[GEN]
for pre,lst in special:
    SPL.append(lst)
    for mi,n in enumerate(MN):
        if any(n.startswith(p_) for p_ in pre): mlist[mi]=len(SPL)-1
# per material: keep 1-3 dominant blocks
order=np.argsort(bmat,kind='stable'); sb=bmat[order]
starts=np.r_[0,np.nonzero(np.diff(sb))[0]+1,len(sb)]
nm=0
for a,b_ in zip(starts[:-1],starts[1:]):
    idx=order[a:b_]; mi=sb[a]; lst=SPL[mlist[mi]]
    g=GAIN if mlist[mi]==0 else autogain(bcol[idx],PAL['build'][lst[0]])
    pen=BPEN if mlist[mi]==0 else None
    k=nearest(bcol[idx],lst,'build',pen,g)
    cnt=np.bincount(k,minlength=len(lst)); top=np.argsort(-cnt)
    keep=[t for t in top[:3] if cnt[t]>=0.15*len(idx)] or [top[0]]
    keep=[lst[t] for t in keep]
    if len(keep)>1:
        k2=nearest(bcol[idx],keep,'build',pen,g)
        bn[idx]=np.array(keep,object)[k2]
    else: bn[idx]=keep[0]
    nm+=1
print('materials',nm,flush=True)
# 6-neighbour majority smoothing on building voxels
BU=sorted(set(bn)); bl=np.searchsorted(BU,bn.astype(str)).astype(np.int32)
LB=np.full((NX,NZ,NY),-1,np.int16)
for it in range(2):
    LB[bs]=bl
    nbl=np.stack([LB[np.clip(bs[0]+dx,0,NX-1),np.clip(bs[1]+dz,0,NZ-1),np.clip(bs[2]+dy,0,NY-1)] for dx,dz,dy in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1))],1)
    best=bl.copy(); bc=np.zeros(len(bl),np.int32)
    for j in range(6):
        c=(nbl==nbl[:,j:j+1]).sum(1)
        u=(nbl[:,j]>=0)&(c>bc); best[u]=nbl[u,j]; bc[u]=c[u]
    ch=(bc>=4)&(best!=bl); bl[ch]=best[ch]
    print('smooth changed',int(ch.sum()),flush=True)
del LB,nbl
bn[:]=np.array(BU,object)[bl]
# chains
chm=mstarts(('dire_chain','bad_chains'))
bn[chm]='@chain'
cand=mstarts(('candles',)); bn[cand]='@candle'
torch=mstarts(('torch','water_creep_camp_torch')); lant=mstarts(('lantern_of_sight',))
shopR=mstarts(('good_shop001','secretshop_radiant')); shopD=mstarts(('bad_shop','secretshop_dire'))
urn=mstarts(('urn',))
stash=mstarts(('neutral_stash_box',))
# ---- architectural trims: corner pillars, copings, plinths ----
TRIM={'stone_bricks':('polished_andesite','mossy_stone_bricks'),'mossy_stone_bricks':('stone_bricks','mossy_cobblestone'),'cracked_stone_bricks':('stone_bricks','cobblestone'),
 'cobblestone':('stone_bricks','mossy_cobblestone'),'mossy_cobblestone':('mossy_stone_bricks','cobblestone'),'polished_andesite':('stone_bricks','andesite'),'andesite':('polished_andesite','cobblestone'),
 'stone':('stone_bricks','cobblestone'),'smooth_stone':('stone_bricks','stone'),'chiseled_stone_bricks':('stone_bricks','stone_bricks'),
 'deepslate_bricks':('polished_deepslate','cobbled_deepslate'),'deepslate_tiles':('polished_deepslate','cobbled_deepslate'),'polished_deepslate':('deepslate_bricks','cobbled_deepslate'),'cobbled_deepslate':('polished_deepslate','deepslate_tiles'),
 'blackstone':('polished_blackstone_bricks','blackstone'),'polished_blackstone':('polished_blackstone_bricks','blackstone'),'polished_blackstone_bricks':('polished_blackstone','blackstone'),'gilded_blackstone':('polished_blackstone','blackstone'),
 'tuff':('polished_tuff','tuff_bricks'),'tuff_bricks':('polished_tuff','tuff'),'polished_tuff':('tuff_bricks','tuff'),'chiseled_tuff':('polished_tuff','tuff'),
 'nether_bricks':('red_nether_bricks','blackstone'),'red_nether_bricks':('nether_bricks','blackstone'),'bricks':('mud_bricks','cobblestone'),'mud_bricks':('packed_mud','cobblestone'),'packed_mud':('mud_bricks','cobblestone'),
 'sandstone':('cut_sandstone','smooth_sandstone'),'cut_sandstone':('smooth_sandstone','sandstone'),'smooth_sandstone':('cut_sandstone','sandstone'),'quartz_block':('quartz_bricks','smooth_stone'),'calcite':('polished_diorite','stone'),'diorite':('polished_diorite','cobblestone'),'polished_diorite':('quartz_bricks','diorite'),
 'granite':('polished_granite','cobblestone'),'polished_granite':('granite','cobblestone'),'prismarine':('prismarine_bricks','dark_prismarine'),'prismarine_bricks':('dark_prismarine','prismarine'),
 'oak_planks':('oak_log|','cobblestone'),'spruce_planks':('spruce_log|','cobblestone'),'dark_oak_planks':('dark_oak_log|','cobbled_deepslate'),'pale_oak_planks':('pale_oak_log|','stone'),'birch_planks':('birch_log|','stone'),
 'jungle_planks':('jungle_log|','cobblestone'),'mangrove_planks':('mangrove_log|','mud_bricks'),'cherry_planks':('cherry_log|','stone_bricks'),'acacia_planks':('acacia_log|','cobblestone'),'bamboo_planks':('bamboo_block|','cobblestone'),'crimson_planks':('crimson_stem|','blackstone')}
SBm=np.zeros(B.shape,bool); SBm[bs]=True
def nb2(dx,dz,dy): return SBm[np.clip(bs[0]+dx,0,NX-1),np.clip(bs[1]+dz,0,NZ-1),np.clip(bs[2]+dy,0,NY-1)]
ex_x=~nb2(1,0,0)|~nb2(-1,0,0); ex_z=~nb2(0,1,0)|~nb2(0,-1,0); ex_up=~nb2(0,0,1)
vedge=ex_x&ex_z&(nb2(0,0,1)|nb2(0,0,-1))
tedge=ex_up&(ex_x|ex_z)&~vedge
plinth=(bs[2]<=gt[bs[0],bs[1]]+1)&(ex_x|ex_z)&~vedge&~tedge
del SBm
istrim=np.array([n in TRIM for n in bn])
nt=0
for msk,kk in ((vedge,0),(tedge,0),(plinth,1)):
    for i in np.nonzero(msk&istrim)[0]:
        t=TRIM[bn[i]][kk]
        if t.endswith('|'): t=t+('y' if msk is vedge else ('x' if ex_z[i] else 'z'))
        bn[i]=t; nt+=1
print('trims',nt,flush=True)
un,inv=np.unique(bn,return_inverse=True)
ids=np.array([0 if n.startswith('@') else (P(n.split('|')[0],axis=n.split('|')[1]) if '|' in n else BP(n)) for n in un],np.uint16)
B[bs]=ids[inv]
solid_build=np.zeros(B.shape,bool); solid_build[bs]=True
def nbi(dx,dz,dy):
    return solid_build[np.clip(bs[0]+dx,0,NX-1),np.clip(bs[1]+dz,0,NZ-1),np.clip(bs[2]+dy,0,NY-1)]
def nb(mask,dx,dz,dy):
    return np.roll(np.roll(np.roll(mask,-dx,0),-dz,1),-dy,2)
hn=nbi(1,0,0).astype(np.uint8)+nbi(-1,0,0)+nbi(0,1,0)+nbi(0,-1,0)
vn=nbi(0,0,1)|nbi(0,0,-1)
postb=(hn==0)
WALL={'stone_bricks':'stone_brick_wall','mossy_stone_bricks':'mossy_stone_brick_wall','cobblestone':'cobblestone_wall','mossy_cobblestone':'mossy_cobblestone_wall','andesite':'andesite_wall','diorite':'diorite_wall','granite':'granite_wall','blackstone':'blackstone_wall','polished_blackstone':'polished_blackstone_wall','polished_blackstone_bricks':'polished_blackstone_brick_wall','cobbled_deepslate':'cobbled_deepslate_wall','polished_deepslate':'polished_deepslate_wall','deepslate_bricks':'deepslate_brick_wall','deepslate_tiles':'deepslate_tile_wall','bricks':'brick_wall','mud_bricks':'mud_brick_wall','nether_bricks':'nether_brick_wall','red_nether_bricks':'red_nether_brick_wall','sandstone':'sandstone_wall','prismarine':'prismarine_wall','tuff':'tuff_wall','tuff_bricks':'tuff_brick_wall','polished_tuff':'polished_tuff_wall','resin_bricks':'resin_brick_wall','stone':'cobblestone_wall','polished_andesite':'andesite_wall','smooth_stone':'stone_brick_wall','calcite':'diorite_wall','polished_diorite':'diorite_wall','polished_granite':'granite_wall','quartz_block':'diorite_wall','cut_sandstone':'sandstone_wall','smooth_sandstone':'sandstone_wall','chiseled_stone_bricks':'stone_brick_wall','cracked_stone_bricks':'stone_brick_wall','basalt':'blackstone_wall','gilded_blackstone':'polished_blackstone_wall','dark_prismarine':'prismarine_wall','prismarine_bricks':'prismarine_wall','chiseled_tuff':'tuff_wall','packed_mud':'mud_brick_wall','dripstone_block':'tuff_wall','smooth_basalt':'cobbled_deepslate_wall','bone_block':'diorite_wall','terracotta':'brick_wall','brown_terracotta':'mud_brick_wall','red_terracotta':'brick_wall'}
FENCE={'oak_planks':'oak_fence','spruce_planks':'spruce_fence','dark_oak_planks':'dark_oak_fence','pale_oak_planks':'pale_oak_fence','cherry_planks':'cherry_fence','birch_planks':'birch_fence','jungle_planks':'jungle_fence','mangrove_planks':'mangrove_fence','bamboo_planks':'bamboo_fence','acacia_planks':'acacia_fence','crimson_planks':'crimson_fence','oak_log':'oak_fence','spruce_log':'spruce_fence','dark_oak_log':'dark_oak_fence','stripped_oak_log':'oak_fence'}
# stairs on top-exposed build voxels with a higher build neighbour on exactly one side
STAIRS={'stone_bricks':'stone_brick_stairs','mossy_stone_bricks':'mossy_stone_brick_stairs','cobblestone':'cobblestone_stairs','mossy_cobblestone':'mossy_cobblestone_stairs','stone':'stone_stairs','andesite':'andesite_stairs','polished_andesite':'polished_andesite_stairs','tuff':'tuff_stairs','tuff_bricks':'tuff_brick_stairs','polished_tuff':'polished_tuff_stairs','mud_bricks':'mud_brick_stairs','deepslate_tiles':'deepslate_tile_stairs','deepslate_bricks':'deepslate_brick_stairs','cobbled_deepslate':'cobbled_deepslate_stairs','polished_deepslate':'polished_deepslate_stairs','blackstone':'blackstone_stairs','polished_blackstone':'polished_blackstone_stairs','polished_blackstone_bricks':'polished_blackstone_brick_stairs','granite':'granite_stairs','polished_granite':'polished_granite_stairs','diorite':'diorite_stairs','polished_diorite':'polished_diorite_stairs','sandstone':'sandstone_stairs','smooth_sandstone':'smooth_sandstone_stairs','bricks':'brick_stairs','nether_bricks':'nether_brick_stairs','red_nether_bricks':'red_nether_brick_stairs','quartz_block':'quartz_stairs','prismarine':'prismarine_stairs','prismarine_bricks':'prismarine_brick_stairs','dark_prismarine':'dark_prismarine_stairs','resin_bricks':'resin_brick_stairs','oak_planks':'oak_stairs','spruce_planks':'spruce_stairs','dark_oak_planks':'dark_oak_stairs','pale_oak_planks':'pale_oak_stairs','cherry_planks':'cherry_stairs','birch_planks':'birch_stairs','jungle_planks':'jungle_stairs','mangrove_planks':'mangrove_stairs','bamboo_planks':'bamboo_stairs','acacia_planks':'acacia_stairs','crimson_planks':'crimson_stairs','cut_copper':'cut_copper_stairs','oxidized_cut_copper':'oxidized_cut_copper_stairs','cracked_stone_bricks':'stone_brick_stairs','smooth_stone':'stone_stairs','calcite':'polished_diorite_stairs','packed_mud':'mud_brick_stairs','cut_sandstone':'smooth_sandstone_stairs','chiseled_stone_bricks':'stone_brick_stairs'}
DIRS=[('east',1,0),('west',-1,0),('south',0,1),('north',0,-1)]
# special functional blocks
def place_list(mask,fn):
    for i in np.nonzero(mask)[0]: fn(bs[0][i],bs[1][i],bs[2][i],i)
air=lambda x,z,y: 0<=x<NX and 0<=z<NZ and 0<=y<NY and B[x,z,y]==0
def chain_fn(x,z,y,i):
    ax='y'
    if solid_build[min(x+1,NX-1),z,y] or solid_build[max(x-1,0),z,y]: ax='x'
    if solid_build[x,min(z+1,NZ-1),y] or solid_build[x,max(z-1,0),y]: ax='z'
    if solid_build[x,z,min(y+1,NY-1)] or solid_build[x,z,max(y-1,0)]: ax='y'
    B[x,z,y]=P('iron_chain',axis=ax,waterlogged='false')
place_list(chm,chain_fn)
def candle_fn(x,z,y,i):
    if air(x,z,y+1) and rng.random()<0.6: B[x,z,y]=P('candle',candles=int(rng.integers(1,5)),lit='true',waterlogged='false')
    else: B[x,z,y]=0
place_list(cand,candle_fn)
def torch_fn(x,z,y,i):
    if air(x,z,y+1): B[x,z,y+1]=P('copper_torch' if not DIRE[x,z] else 'soul_torch')
place_list(torch&~nbi(0,0,1),torch_fn)
def lant_fn(x,z,y,i):
    if air(x,z,y+1): B[x,z,y+1]=P('copper_lantern',hanging='false',waterlogged='false')
place_list(lant&~nbi(0,0,1),lant_fn)
nshelf=0
def urn_fn(x,z,y,i):
    if air(x,z,y+1) and rng.random()<0.5: B[x,z,y+1]=P('decorated_pot',cracked=str(rng.random()<0.3).lower(),facing=DIRS[int(rng.integers(4))][0],waterlogged='false')
place_list(urn&~nbi(0,0,1),urn_fn)
place_list(stash,lambda x,z,y,i: B.__setitem__((x,z,y),P('barrel',facing='up',open='false')))
nh=0
print('specials shelves',nshelf,'hanging',nh,time.time()-T,flush=True)
np.save(OD+'B_stage1.npy',B); json.dump(pal,open(OD+'pal_stage1.json','w'))
print('DONE',len(pal),time.time()-T)

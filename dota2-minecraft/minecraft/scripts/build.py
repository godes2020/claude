import numpy as np, json, time
from scipy import ndimage as ndi
T=time.time(); D='/home/user/dota_work/mc/'
G=json.load(open(D+'grid.json')); S,XMAX,YMAX=G['S'],G['XMAX'],G['YMAX']
meta=json.load(open(D+'meta.json')); MN=[m['name'].lower() for m in meta['mats']]
PAL=json.load(open(D+'palette.json'))
CAT=np.load(D+'CAT.npy'); COL=np.load(D+'COL.npy'); MAT=np.load(D+'MAT.npy')
NX,NZ,NY0=CAT.shape; NY=NY0+6
pad=lambda a,v: np.concatenate([a,np.full(a.shape[:2]+(6,)+a.shape[3:],v,a.dtype)],axis=2)
CAT=pad(CAT,0); COL=pad(COL,0); MAT=pad(MAT,-1)
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
def nearest(cols,names,src,pen=None,gain=1.0,noise=6.0):
    pc=np.array([PAL[src][n] for n in names],np.float32)
    c=cols.astype(np.float32)*gain+rng.normal(0,noise,cols.shape).astype(np.float32)
    out=np.empty(len(c),np.int32); pn=np.zeros(len(names),np.float32) if pen is None else np.array([pen.get(n,0) for n in names],np.float32)
    for i in range(0,len(c),500000):
        cc=c[i:i+500000]; rm=(cc[:,None,0]+pc[None,:,0])/2
        dr=cc[:,None,0]-pc[None,:,0]; dg=cc[:,None,1]-pc[None,:,1]; db=cc[:,None,2]-pc[None,:,2]
        d=np.sqrt((2+rm/256)*dr*dr+4*dg*dg+(2+(255-rm)/256)*db*db)+pn
        out[i:i+500000]=d.argmin(1)
    return out
def autogain(cols,target):
    l=np.median(lum(cols.astype(np.float32))); return float(np.clip(lum(np.array(target,np.float32))/max(l,1),0.6,2.5))
ii,jj=np.indices((NX,NZ))
xw=XMAX-(jj+0.5)/S; yw=YMAX-(ii+0.5)/S
side=(xw-yw)+ndi.gaussian_filter(rng.normal(0,25,(NX,NZ)),6)
DIRE=side>0
print('load',time.time()-T,flush=True)
# ---------------- ground ----------------
g=(CAT==4)|(CAT==5)
has=g.any(2); gtop=(NY-1-np.argmax(g[:,:,::-1],axis=2)).astype(np.int32); gtop[~has]=-1
inside=ndi.binary_fill_holes(ndi.binary_closing(has,iterations=4))
di,(ni,nj)=ndi.distance_transform_edt(~has,return_indices=True)
miss=inside&~has
gtop[miss]=gtop[ni[miss],nj[miss]]
tcol=COL[ii,jj,np.maximum(gtop,0)].copy(); tcol[miss]=tcol[ni[miss],nj[miss]]
tlava=(CAT[ii,jj,np.maximum(gtop,0)]==5)&inside
tmat=MAT[ii,jj,np.maximum(gtop,0)]
L=np.load(D+'L_decal.npz'); Hd,Cd=L['H'],L['C']
path=inside&(Hd>=gtop-1.5)&(Hd<=gtop+3)
tcol[path]=Cd[path]
Lw=np.load(D+'L_water.npz'); Hw=Lw['H']
wl=np.floor(Hw-0.3).astype(np.int32); wl[Hw<0]=-1
water=inside&(Hw>=0)&(Hw-gtop>=0.3)&(Hw-gtop<=8)
water=ndi.binary_opening(water,iterations=1)
wd=ndi.distance_transform_edt(water)
extra=(wd>=4).astype(np.int32)+(wd>=9)
surf=np.maximum(np.floor(Hw-0.3).astype(np.int32),gtop)
bed=np.minimum(gtop,surf-1)-extra
wl=np.where(water,surf,-1)
# smooth isolated 1-voxel spikes/pits in gtop
med=ndi.median_filter(gtop,3)
sp=inside&~water&(np.abs(gtop-med)>=2)&(ndi.maximum_filter(gtop,3)-ndi.minimum_filter(gtop,3)<=3)
gtop[sp]=med[sp]
gtop[water]=bed[water]
print('ground cols',inside.sum(),'water',water.sum(),'path',path.sum(),'lava',tlava.sum(),time.time()-T,flush=True)
RAD_TOP=['grass_block','moss_block','podzol','coarse_dirt','rooted_dirt','gravel','packed_mud','mud','stone','andesite','tuff','cobblestone','mossy_cobblestone','stone_bricks','mossy_stone_bricks','calcite','dirt','clay','polished_andesite']
RAD_PEN={'grass_block':-30,'moss_block':-5,'calcite':40,'clay':30,'mud':20,'stone_bricks':30,'polished_andesite':30}
DIRE_TOP=['coarse_dirt','rooted_dirt','gravel','packed_mud','mud','tuff','basalt','blackstone','deepslate','cobbled_deepslate','soul_soil','dirt','podzol','andesite','cobblestone','smooth_basalt','pale_moss_block','muddy_mangrove_roots','gray_terracotta','brown_terracotta']
DIRE_PEN={'coarse_dirt':-3,'gravel':-4,'tuff':-3,'rooted_dirt':-3,'packed_mud':-5,'soul_soil':-5,'pale_moss_block':30,'gray_terracotta':20,'brown_terracotta':10}
PATH=['dirt_path','coarse_dirt','gravel','packed_mud','rooted_dirt','mud_bricks','stone_bricks','cobblestone','mossy_cobblestone','polished_andesite','tuff_bricks','andesite','cracked_stone_bricks','polished_blackstone_bricks','deepslate_tiles','dirt','mossy_stone_bricks','smooth_stone']
PATH_PEN={'dirt_path':-25,'coarse_dirt':-10,'gravel':-5}
BED=['mud','clay','gravel','sand','coarse_dirt','dirt','packed_mud','mossy_cobblestone','tuff','muddy_mangrove_roots','andesite']
ROCK_R=['stone','andesite','tuff','cobblestone','mossy_cobblestone','granite','dripstone_block','mossy_stone_bricks','stone_bricks','packed_mud','mud_bricks','dirt','coarse_dirt','moss_block','cracked_stone_bricks','deepslate','cobbled_deepslate']
ROCK_D=['tuff','basalt','blackstone','deepslate','cobbled_deepslate','andesite','stone','cobblestone','smooth_basalt','polished_blackstone','packed_mud','mud_bricks','coarse_dirt','dripstone_block','deepslate_tiles','gray_terracotta','brown_terracotta','polished_deepslate']
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
print('top assigned',time.time()-T,flush=True)
# sides/interior: per column fill from gfloor..gtop-1
gt=np.where(inside,gtop,-1)
nmin=ndi.minimum_filter(np.where(inside,gt,0),3)
gfloor=np.clip(np.minimum(nmin,gt)-3,0,None)
# shell colours forward/back filled along y
shell=(CAT==4)
yy=np.arange(NY)[None,None,:]
idxs=np.where(shell,yy,0); np.maximum.accumulate(idxs,axis=2,out=idxs)
idxs2=np.where(shell,yy,NY-1)[:,:,::-1]; idxs2=np.minimum.accumulate(idxs2,axis=2)[:,:,::-1]
src=np.where(shell.any(2)[:,:,None],np.where(np.take_along_axis(shell,idxs,2),idxs,idxs2),0)
below=(yy>=gfloor[:,:,None])&(yy<gt[:,:,None])
# only voxels visible (exposed horizontally) need colour-matched blocks
sel=np.nonzero(below)
print('fill voxels',len(sel[0]),time.time()-T,flush=True)
expo=np.zeros(len(sel[0]),bool)
for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
    a=np.clip(sel[0]+dx,0,NX-1); b=np.clip(sel[1]+dz,0,NZ-1)
    expo|=gt[a,b]<sel[2]
cc=COL[sel[0],sel[1],src[sel]]
dirt_like=np.isin(topname[sel[0],sel[1]],['grass_block','moss_block','podzol','rooted_dirt','dirt'])
depth=gt[sel[0],sel[1]]-sel[2]
names=np.empty(len(sel[0]),object)
dmask=DIRE[sel[0],sel[1]]
names[:]=np.where(dmask,'deepslate','stone')
names[dirt_like&(depth<=3)]='dirt'
for msk,lst in ((expo&~dmask,ROCK_R),(expo&dmask,ROCK_D)):
    if msk.any():
        k=nearest(cc[msk],lst,'ground',None,autogain(cc[msk],PAL['ground']['stone']))
        names[msk]=np.array(lst,object)[k]
edge=~ndi.binary_erosion(inside,iterations=2)
em=edge[sel[0],sel[1]]
names[em]=np.where(rng.random(em.sum())<0.5,'tuff',np.where(rng.random(em.sum())<0.5,'deepslate','cobbled_deepslate'))
un,inv=np.unique(names,return_inverse=True)
B[sel]=np.array([BP(n) for n in un],np.uint16)[inv]
tsel=np.nonzero(inside)
un,inv=np.unique(topname[tsel],return_inverse=True)
B[tsel[0],tsel[1],gt[tsel]]=np.array([BP(n) for n in un],np.uint16)[inv]
del idxs,idxs2,src,below
print('ground placed',time.time()-T,flush=True)
# lava: contained cells -> lava
lv=np.nonzero(inside&tlava)
cont=np.ones(len(lv[0]),bool)
for dx,dz in ((1,0),(-1,0),(0,1),(0,-1)):
    a=np.clip(lv[0]+dx,0,NX-1); b=np.clip(lv[1]+dz,0,NZ-1)
    cont&=(gt[a,b]>=gt[lv])
B[lv[0][cont],lv[1][cont],gt[lv][cont]]=P('lava',level=0)
# ---------------- water ----------------
wsel=np.nonzero(water)
WB=P('water',level=0)
for k in range(1,40):
    m=wl[wsel]>=gt[wsel]+k
    if not m.any(): break
    B[wsel[0][m],wsel[1][m],gt[wsel][m]+k]=WB
wdepth=np.where(water,wl-gt,0)
print('water placed',time.time()-T,flush=True)
np.savez(D+'stage_ground.npz',gt=gt,inside=inside,water=water,wl=wl,DIRE=DIRE,path=path)
# ---------------- buildings ----------------
bm=(CAT==8)
bs=np.nonzero(bm)
bmat=MAT[bs]; bcol=COL[bs]
mname=np.array(MN+[''],object)[bmat]
def mstarts(prefixes): return np.array([any(n.startswith(p) for p in prefixes) for n in MN]+[False])[bmat]
GEN=[n for n in PAL['build'] if not n.endswith('_wool') and n not in ('oak_log','spruce_log','dark_oak_log','stripped_oak_log','shroomlight','nether_wart_block','sea_lantern','blue_ice','lapis_block','magma_block','crying_obsidian','tuff_bricks2','amethyst_block','gold_block','iron_block','moss_block')]
bn=np.empty(len(bs[0]),object)
k=nearest(bcol,GEN,'build',{'stone_bricks':-8,'mossy_stone_bricks':-4,'polished_andesite':-3,'cobblestone':-3},autogain(bcol,PAL['build']['stone_bricks']),4)
bn[:]=np.array(GEN,object)[k]
special=[
 (('team_banner_radiant','bannerbase_radiant','team_logo_radiant'),['green_wool','lime_wool','white_wool','yellow_wool','gold_block','oak_planks','spruce_planks','stone_bricks']),
 (('team_banner_dire','bannerbase_dire','team_logo_dire'),['red_wool','black_wool','brown_wool','orange_wool','nether_bricks','red_nether_bricks','polished_blackstone','dark_oak_planks']),
 (('crystal',),['amethyst_block','blue_ice','light_blue_wool','prismarine','sea_lantern']),
 (('aegis','gold','radiant_ancient001'),['gold_block','raw_gold_block','white_wool','calcite','quartz_block','light_blue_terracotta','prismarine']),
 (('leanto_fur',),['brown_wool','white_wool','black_wool']),
 (('lava','cracks'),['magma_block','shroomlight','obsidian']),
 (('log002','leanto_sticks','bad_sticks','wood_fence','wood_walls','water_creep_camp_huts','water_creep_camp_fish','neutral_stash'),['oak_planks','spruce_planks','dark_oak_planks','pale_oak_planks','jungle_planks','mangrove_planks','birch_planks','oak_log','spruce_log','dark_oak_log','stripped_oak_log','bamboo_planks']),
]
for pre,lst in special:
    msk=mstarts(pre)
    if msk.any(): bn[msk]=np.array(lst,object)[nearest(bcol[msk],lst,'build',None,autogain(bcol[msk],PAL['build'][lst[0]]),4)]
# chains
chm=mstarts(('dire_chain','bad_chains'))
bn[chm]='@chain'
cand=mstarts(('candles',)); bn[cand]='@candle'
torch=mstarts(('torch','water_creep_camp_torch')); lant=mstarts(('lantern_of_sight',))
shopR=mstarts(('good_shop001','secretshop_radiant')); shopD=mstarts(('bad_shop','secretshop_dire'))
urn=mstarts(('urn',))
stash=mstarts(('neutral_stash_box',))
un,inv=np.unique(bn,return_inverse=True)
ids=np.array([0 if n.startswith('@') else BP(n) for n in un],np.uint16)
B[bs]=ids[inv]
solid_build=np.zeros(B.shape,bool); solid_build[bs]=True
def nb(mask,dx,dz,dy):
    return np.roll(np.roll(np.roll(mask,-dx,0),-dz,1),-dy,2)
hn=nb(solid_build,1,0,0).astype(np.uint8)+nb(solid_build,-1,0,0)+nb(solid_build,0,1,0)+nb(solid_build,0,-1,0)
vn=nb(solid_build,0,0,1)|nb(solid_build,0,0,-1)
post=solid_build&(hn==0)
WALL={'stone_bricks':'stone_brick_wall','mossy_stone_bricks':'mossy_stone_brick_wall','cobblestone':'cobblestone_wall','mossy_cobblestone':'mossy_cobblestone_wall','andesite':'andesite_wall','diorite':'diorite_wall','granite':'granite_wall','blackstone':'blackstone_wall','polished_blackstone':'polished_blackstone_wall','polished_blackstone_bricks':'polished_blackstone_brick_wall','cobbled_deepslate':'cobbled_deepslate_wall','polished_deepslate':'polished_deepslate_wall','deepslate_bricks':'deepslate_brick_wall','deepslate_tiles':'deepslate_tile_wall','bricks':'brick_wall','mud_bricks':'mud_brick_wall','nether_bricks':'nether_brick_wall','red_nether_bricks':'red_nether_brick_wall','sandstone':'sandstone_wall','prismarine':'prismarine_wall','tuff':'tuff_wall','tuff_bricks':'tuff_brick_wall','polished_tuff':'polished_tuff_wall','resin_bricks':'resin_brick_wall','stone':'cobblestone_wall','polished_andesite':'andesite_wall','smooth_stone':'stone_brick_wall','calcite':'diorite_wall','polished_diorite':'diorite_wall','polished_granite':'granite_wall','quartz_block':'diorite_wall','cut_sandstone':'sandstone_wall','smooth_sandstone':'sandstone_wall','chiseled_stone_bricks':'stone_brick_wall','cracked_stone_bricks':'stone_brick_wall','basalt':'blackstone_wall','gilded_blackstone':'polished_blackstone_wall','dark_prismarine':'prismarine_wall','prismarine_bricks':'prismarine_wall','chiseled_tuff':'tuff_wall','packed_mud':'mud_brick_wall','dripstone_block':'tuff_wall','smooth_basalt':'cobbled_deepslate_wall','bone_block':'diorite_wall','terracotta':'brick_wall','brown_terracotta':'mud_brick_wall','red_terracotta':'brick_wall'}
FENCE={'oak_planks':'oak_fence','spruce_planks':'spruce_fence','dark_oak_planks':'dark_oak_fence','pale_oak_planks':'pale_oak_fence','cherry_planks':'cherry_fence','birch_planks':'birch_fence','jungle_planks':'jungle_fence','mangrove_planks':'mangrove_fence','bamboo_planks':'bamboo_fence','acacia_planks':'acacia_fence','crimson_planks':'crimson_fence','oak_log':'oak_fence','spruce_log':'spruce_fence','dark_oak_log':'dark_oak_fence','stripped_oak_log':'oak_fence'}
pidx=np.nonzero(post[bs])[0]
for i in pidx:
    n=bn[i]
    if n in WALL: B[bs[0][i],bs[1][i],bs[2][i]]=P(WALL[n],east='none',north='none',south='none',west='none',up='true',waterlogged='false')
    elif n in FENCE: B[bs[0][i],bs[1][i],bs[2][i]]=P(FENCE[n],east='false',north='false',south='false',west='false',waterlogged='false')
print('posts',len(pidx),time.time()-T,flush=True)
# stairs on top-exposed build voxels with a higher build neighbour on exactly one side
STAIRS={'stone_bricks':'stone_brick_stairs','mossy_stone_bricks':'mossy_stone_brick_stairs','cobblestone':'cobblestone_stairs','mossy_cobblestone':'mossy_cobblestone_stairs','stone':'stone_stairs','andesite':'andesite_stairs','polished_andesite':'polished_andesite_stairs','tuff':'tuff_stairs','tuff_bricks':'tuff_brick_stairs','polished_tuff':'polished_tuff_stairs','mud_bricks':'mud_brick_stairs','deepslate_tiles':'deepslate_tile_stairs','deepslate_bricks':'deepslate_brick_stairs','cobbled_deepslate':'cobbled_deepslate_stairs','polished_deepslate':'polished_deepslate_stairs','blackstone':'blackstone_stairs','polished_blackstone':'polished_blackstone_stairs','polished_blackstone_bricks':'polished_blackstone_brick_stairs','granite':'granite_stairs','polished_granite':'polished_granite_stairs','diorite':'diorite_stairs','polished_diorite':'polished_diorite_stairs','sandstone':'sandstone_stairs','smooth_sandstone':'smooth_sandstone_stairs','bricks':'brick_stairs','nether_bricks':'nether_brick_stairs','red_nether_bricks':'red_nether_brick_stairs','quartz_block':'quartz_stairs','prismarine':'prismarine_stairs','prismarine_bricks':'prismarine_brick_stairs','dark_prismarine':'dark_prismarine_stairs','resin_bricks':'resin_brick_stairs','oak_planks':'oak_stairs','spruce_planks':'spruce_stairs','dark_oak_planks':'dark_oak_stairs','pale_oak_planks':'pale_oak_stairs','cherry_planks':'cherry_stairs','birch_planks':'birch_stairs','jungle_planks':'jungle_stairs','mangrove_planks':'mangrove_stairs','bamboo_planks':'bamboo_stairs','acacia_planks':'acacia_stairs','crimson_planks':'crimson_stairs','cut_copper':'cut_copper_stairs','oxidized_cut_copper':'oxidized_cut_copper_stairs','cracked_stone_bricks':'stone_brick_stairs','smooth_stone':'stone_stairs','calcite':'polished_diorite_stairs','packed_mud':'mud_brick_stairs','cut_sandstone':'smooth_sandstone_stairs','chiseled_stone_bricks':'stone_brick_stairs'}
top_exp=solid_build&~nb(solid_build,0,0,1)&~post
DIRS=[('east',1,0),('west',-1,0),('south',0,1),('north',0,-1)]
up_n={d:nb(solid_build,dx,dz,1) for d,dx,dz in DIRS}
cnt=sum(up_n[d].astype(np.uint8) for d,_,_ in DIRS)
st=top_exp&(cnt==1)&(hn>=2)
sidx=np.nonzero(st[bs])[0]; ns=0
for i in sidx:
    n=bn[i]
    if n not in STAIRS: continue
    x,z,y=bs[0][i],bs[1][i],bs[2][i]
    for d,dx,dz in DIRS:
        if up_n[d][x,z,y]:
            B[x,z,y]=P(STAIRS[n],facing=d,half='bottom',shape='straight',waterlogged='false'); ns+=1; break
print('stairs',ns,time.time()-T,flush=True)
del up_n,cnt,st,top_exp
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
place_list(torch&~nb(solid_build,0,0,1)[bs],torch_fn)
def lant_fn(x,z,y,i):
    if air(x,z,y+1): B[x,z,y+1]=P('copper_lantern',hanging='false',waterlogged='false')
place_list(lant&~nb(solid_build,0,0,1)[bs],lant_fn)
nshelf=0
def shelf_fn(x,z,y,i,wood):
    global nshelf
    for d,dx,dz in DIRS:
        if air(x+dx,z+dz,y):
            B[x,z,y]=P(wood,facing=d,powered='false',side_chain='unconnected',waterlogged='false'); nshelf+=1; return
place_list(shopR,lambda x,z,y,i: shelf_fn(x,z,y,i,'pale_oak_shelf'))
place_list(shopD,lambda x,z,y,i: shelf_fn(x,z,y,i,'dark_oak_shelf'))
def urn_fn(x,z,y,i):
    if air(x,z,y+1) and rng.random()<0.5: B[x,z,y+1]=P('decorated_pot',cracked=str(rng.random()<0.3).lower(),facing=DIRS[int(rng.integers(4))][0],waterlogged='false')
place_list(urn&~nb(solid_build,0,0,1)[bs],urn_fn)
place_list(stash,lambda x,z,y,i: B.__setitem__((x,z,y),P('barrel',facing='up',open='false')))
# lanterns on wall posts tops, hanging lanterns under overhangs
pt=np.nonzero(post[bs]&~vn[bs])[0]
for i in np.nonzero(post[bs])[0]:
    x,z,y=bs[0][i],bs[1][i],bs[2][i]
    if air(x,z,y+1) and not solid_build[x,z,max(y-1,0)]==False and rng.random()<0.35:
        B[x,z,y+1]=P('soul_lantern' if DIRE[x,z] else 'lantern',hanging='false',waterlogged='false')
under=solid_build&~nb(solid_build,0,0,-1)
uidx=np.nonzero(under[bs])[0]; nh=0
for i in uidx:
    x,z,y=bs[0][i],bs[1][i],bs[2][i]
    if y-gt[x,z]>=5 and rng.random()<0.03 and air(x,z,y-1) and air(x,z,y-2) and air(x,z,y-3):
        L_=int(rng.integers(1,3))
        for k in range(1,L_+1): B[x,z,y-k]=P('iron_chain',axis='y',waterlogged='false')
        B[x,z,y-L_-1]=P('soul_lantern' if DIRE[x,z] else ('copper_lantern' if rng.random()<0.5 else 'lantern'),hanging='true',waterlogged='false'); nh+=1
print('specials shelves',nshelf,'hanging',nh,time.time()-T,flush=True)
np.save(D+'B_stage1.npy',B); json.dump(pal,open(D+'pal_stage1.json','w'))
print('DONE',len(pal),time.time()-T)

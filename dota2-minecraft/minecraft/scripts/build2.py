import numpy as np, json, time
from scipy import ndimage as ndi
T=time.time(); D='/home/user/dota_work/mc/'
meta=json.load(open(D+'meta.json')); MN=[m['name'].lower() for m in meta['mats']]
PAL=json.load(open(D+'palette.json'))
CAT=np.load(D+'CAT.npy'); COL=np.load(D+'COL.npy'); MAT=np.load(D+'MAT.npy')
B=np.load(D+'B_stage1.npy'); pal=json.load(open(D+'pal_stage1.json')); pid={s:i for i,s in enumerate(pal)}
NX,NZ,NY=B.shape; pd=NY-CAT.shape[2]
pad=lambda a,v: np.concatenate([a,np.full(a.shape[:2]+(pd,)+a.shape[3:],v,a.dtype)],axis=2)
CAT=pad(CAT,0); COL=pad(COL,0); MAT=pad(MAT,-1)
SG=np.load(D+'stage_ground.npz'); gt,inside,water,wl,DIRE=SG['gt'],SG['inside'],SG['water'],SG['wl'],SG['DIRE']
rng=np.random.default_rng(11)
def P(name,**pr):
    s='minecraft:'+name+('['+','.join(f'{k}={str(v).lower()}' for k,v in sorted(pr.items()))+']' if pr else '')
    if s not in pid: pid[s]=len(pal); pal.append(s)
    return pid[s]
LEAFB={'oak_leaves','dark_oak_leaves','spruce_leaves','birch_leaves','jungle_leaves','azalea_leaves','flowering_azalea_leaves','cherry_leaves','pale_oak_leaves','mangrove_leaves','acacia_leaves'}
def LP(n): return P(n,distance=7,persistent='true',waterlogged='false') if n in LEAFB else P(n)
def lum(c): return c[...,0]*0.3+c[...,1]*0.59+c[...,2]*0.11
def nearest(cols,names,src,gain=1.0,noise=6.0,pen=None):
    pc=np.array([PAL[src][n] for n in names],np.float32)
    c=cols.astype(np.float32)*gain+rng.normal(0,noise,cols.shape).astype(np.float32)
    pn=np.zeros(len(names),np.float32) if pen is None else np.array([pen.get(n,0) for n in names],np.float32)
    rm=(c[:,None,0]+pc[None,:,0])/2; dr=c[:,None,0]-pc[None,:,0]; dg=c[:,None,1]-pc[None,:,1]; db=c[:,None,2]-pc[None,:,2]
    return (np.sqrt((2+rm/256)*dr*dr+4*dg*dg+(2+(255-rm)/256)*db*db)+pn).argmin(1)
def autogain(cols,ref):
    return float(np.clip(lum(np.array(ref,np.float32))/max(np.median(lum(cols.astype(np.float32))),1),0.6,2.5))
# --------- families ----------
OAKL=['oak_leaves','dark_oak_leaves','jungle_leaves','azalea_leaves','flowering_azalea_leaves','mangrove_leaves','acacia_leaves','birch_leaves','moss_block']
FAM=[ # prefix, log radiant, log dire, leaves list
 ('tree_pine','spruce_log','spruce_log',['spruce_leaves','dark_oak_leaves','mangrove_leaves','oak_leaves']),
 ('tree_oak','oak_log','dark_oak_log',OAKL),
 ('tree_redblossom','dark_oak_log','dark_oak_log',['nether_wart_block','shroomlight','acacia_leaves','cherry_leaves','oak_leaves','dark_oak_leaves']),
 ('tree_blossoms_white','cherry_log','cherry_log',['cherry_leaves','pale_oak_leaves','birch_leaves','flowering_azalea_leaves','oak_leaves']),
 ('tree_magical_white','birch_log','birch_log',['pale_oak_leaves','birch_leaves','cherry_leaves','oak_leaves']),
 ('tree_magical_pink','cherry_log','cherry_log',['cherry_leaves','flowering_azalea_leaves','pale_oak_leaves']),
 ('tree_plumblossom','cherry_log','cherry_log',['cherry_leaves','flowering_azalea_leaves']),
 ('tree_bamboo','bamboo_block','bamboo_block',['jungle_leaves','azalea_leaves','oak_leaves','acacia_leaves']),
 ('dire_tree','dark_oak_log','dark_oak_log',['pale_oak_leaves','dark_oak_leaves','moss_block','mangrove_leaves','spruce_leaves']),
 ('tree_gnarly','pale_oak_log','pale_oak_log',['pale_oak_leaves','dark_oak_leaves']),
 ('tree_cine','oak_log','dark_oak_log',OAKL),
 ('roots','mangrove_log','mangrove_log',['azalea_leaves','oak_leaves','mangrove_leaves','flowering_azalea_leaves']),
 ('radiant_ancient','oak_log','oak_log',['flowering_azalea_leaves','azalea_leaves','oak_leaves','cherry_leaves']),
 ('team_portal','oak_log','oak_log',['flowering_azalea_leaves','azalea_leaves','oak_leaves']),
]
fam_of=np.full(len(MN)+1,1,np.int16)
for i,n in enumerate(MN):
    for f,(p,_,_,_) in enumerate(FAM):
        if n.startswith(p): fam_of[i]=f; break
# ---------- wood -------------
wood=(CAT==7)
ws=np.nonzero(wood); wf=fam_of[MAT[ws]]; wdire=DIRE[ws[0],ws[1]]
wc=COL[ws]
cnt=ndi.convolve(wood.astype(np.uint8),np.ones((3,3,3),np.uint8),mode='constant')[ws]
ax_cnt=np.stack([wood[np.clip(ws[0]+1,0,NX-1),ws[1],ws[2]].astype(int)+wood[np.clip(ws[0]-1,0,NX-1),ws[1],ws[2]],
                 wood[ws[0],np.clip(ws[1]+1,0,NZ-1),ws[2]].astype(int)+wood[ws[0],np.clip(ws[1]-1,0,NZ-1),ws[2]],
                 wood[ws[0],ws[1],np.clip(ws[2]+1,0,NY-1)].astype(int)+wood[ws[0],ws[1],np.clip(ws[2]-1,0,NY-1)]],1)
ax_cnt[:,2]+=1  # prefer vertical
axis=np.array(['x','z','y'])[ax_cnt.argmax(1)]
logname=np.array([FAM[f][2] if d else FAM[f][1] for f,d in zip(wf,wdire)],object)
dt=(wf==8)|(wf==9)
l=lum(wc.astype(np.float32))
logname[dt&(l>np.percentile(l[dt],70))]='pale_oak_log'
logname[dt&(l<np.percentile(l[dt],15))]='spruce_log'
thin=cnt<=4
FENCE={'oak_log':'oak_fence','spruce_log':'spruce_fence','dark_oak_log':'dark_oak_fence','pale_oak_log':'pale_oak_fence','cherry_log':'cherry_fence','birch_log':'birch_fence','mangrove_log':'mangrove_fence','bamboo_block':'bamboo_fence'}
BUTTON={'oak_log':'oak_button','spruce_log':'spruce_button','dark_oak_log':'dark_oak_button','pale_oak_log':'pale_oak_button','cherry_log':'cherry_button','birch_log':'birch_button','mangrove_log':'mangrove_button','bamboo_block':'bamboo_button'}
key=np.char.add(logname.astype(str),np.char.add('|',np.where(thin,'F',axis)))
un,inv=np.unique(key,return_inverse=True)
ids=[]
for k in un:
    n,a=k.split('|')
    ids.append(P(FENCE[n],east='false',north='false',south='false',west='false',waterlogged='false') if a=='F' else P(n,axis=a))
B[ws]=np.array(ids,np.uint16)[inv]
print('wood',len(ws[0]),'fences',thin.sum(),time.time()-T,flush=True)
# ---------- leaves -------------
lv=(CAT==6)
ls=np.nonzero(lv); lf=fam_of[MAT[ls]]; lc=COL[ls]
names=np.empty(len(ls[0]),object)
for f,(p,_,_,lst) in enumerate(FAM):
    m=lf==f
    if not m.any(): continue
    pen={'moss_block':15,'shroomlight':20 if f!=2 else -10,'nether_wart_block':-45 if f==2 else 0,'birch_leaves':18 if f in (1,10) else 0}
    k=nearest(lc[m],lst,'leaves',autogain(lc[m],PAL['leaves'][lst[0]]),8,pen)
    names[m]=np.array(lst,object)[k]
    if f==2:  # red autumn trees: texture is a grey tintable, force red/orange foliage
        r=rng.random(m.sum()); ll=lum(lc[m].astype(np.float32)); dk=ll<np.percentile(ll,25)
        names[m]=np.where(dk,'dark_oak_leaves',np.where(r<0.08,'shroomlight',np.where(r<0.18,'acacia_leaves','nether_wart_block')))
un,inv=np.unique(names,return_inverse=True)
B[ls]=np.array([LP(n) for n in un],np.uint16)[inv]
print('leaves',len(ls[0]),dict(zip(un,np.bincount(inv))),time.time()-T,flush=True)
# ---------- vines -------------
vs=np.nonzero(CAT==3); nv=0
solid=B>0
for x,z,y in zip(*vs):
    if B[x,z,y]: continue
    pr={'east':solid[min(x+1,NX-1),z,y],'west':solid[max(x-1,0),z,y],'south':solid[x,min(z+1,NZ-1),y],'north':solid[x,max(z-1,0),y],'up':solid[x,z,min(y+1,NY-1)]}
    if any(pr.values()): B[x,z,y]=P('vine',**{k:str(bool(v)).lower() for k,v in pr.items()}); nv+=1
print('vines',nv,time.time()-T,flush=True)
# ---------- tree details: buttons on trunks, hanging vines/moss -------------
air=lambda x,z,y: 0<=x<NX and 0<=z<NZ and 0<=y<NY and B[x,z,y]==0
DIRS=[('east',1,0),('west',-1,0),('south',0,1),('north',0,-1)]
nb=0
for i in np.nonzero(~thin&(rng.random(len(ws[0]))<0.02))[0]:
    x,z,y=ws[0][i],ws[1][i],ws[2][i]
    d,dx,dz=DIRS[int(rng.integers(4))]
    if air(x+dx,z+dz,y) and y>gt[x,z]: B[x+dx,z+dz,y]=P(BUTTON[logname[i]],face='wall',facing=d,powered='false'); nb+=1
# small trunk details: fences sticking out as twigs
ntw=0
for i in np.nonzero(~thin&(rng.random(len(ws[0]))<0.006))[0]:
    x,z,y=ws[0][i],ws[1][i],ws[2][i]
    d,dx,dz=DIRS[int(rng.integers(4))]
    if air(x+dx,z+dz,y) and air(x+dx,z+dz,y+1) and y>gt[x,z]+2:
        B[x+dx,z+dz,y]=P(FENCE[logname[i]],east='false',north='false',south='false',west='false',waterlogged='false'); ntw+=1
lbot=np.nonzero(lv&~np.roll(lv,1,axis=2))  # leaf voxels with no leaf below
nhang=0
for x,z,y in zip(*lbot):
    if not (B[x,z,y]>0 and B[x,z,y-1]==0 and y-1>gt[x,z]+2): continue
    r=rng.random()
    if DIRE[x,z]:
        if r<0.10:
            L=int(rng.integers(1,5))
            for k in range(1,L+1):
                if not air(x,z,y-k) or y-k<=gt[x,z]+1: L=k-1; break
                B[x,z,y-k]=P('pale_hanging_moss',tip='false')
            if L>0: B[x,z,y-L]=P('pale_hanging_moss',tip='true'); nhang+=1
    else:
        if r<0.035:
            L=int(rng.integers(1,6))
            for k in range(1,L+1):
                if not air(x,z,y-k) or y-k<=gt[x,z]+1: L=k-1; break
                B[x,z,y-k]=P('cave_vines_plant',berries=str(rng.random()<0.3).lower())
            if L>0: B[x,z,y-L]=P('cave_vines',age=int(rng.integers(0,26)),berries=str(rng.random()<0.4).lower()); nhang+=1
        elif r<0.04: B[x,z,y-1]=P('spore_blossom'); nhang+=1
        elif r<0.05: B[x,z,y-1]=P('hanging_roots',waterlogged='false')
print('buttons',nb,'twigs',ntw,'hanging',nhang,time.time()-T,flush=True)
# ---------- ground vegetation -------------
canopy=ndi.maximum_filter((lv.any(2)).astype(np.uint8),5)>0
Lp=np.load(D+'L_plant.npz'); Hp,Cp,Mp=Lp['H'],Lp['C'],Lp['M']
pname=np.array(MN+[''],object)[np.where(Mp>=0,Mp,len(MN))]
topid=B[np.arange(NX)[:,None],np.arange(NZ)[None,:],np.clip(gt,0,NY-1)]
topn=np.array([s.split('[')[0].split(':')[1] for s in pal],object)[topid]
gx,gz=np.nonzero(inside&~water)
ok=np.array([air(x,z,gt[x,z]+1) for x,z in zip(gx,gz)])
gx,gz=gx[ok],gz[ok]
FLW=['poppy','dandelion','cornflower','oxeye_daisy','azure_bluet','allium','blue_orchid','red_tulip','orange_tulip','pink_tulip','white_tulip','lily_of_the_valley','torchflower']
nearwater=ndi.binary_dilation(water,iterations=6)
stats={}
def put(x,z,y,n,**pr):
    B[x,z,y]=P(n,**pr); stats[n]=stats.get(n,0)+1
def tall(x,z,y,n):
    if air(x,z,y+1): put(x,z,y,n,half='lower'); put(x,z,y+1,n,half='upper')
HORZ=['north','south','east','west']
for x,z in zip(gx,gz):
    y=gt[x,z]+1; t=topn[x,z]; r=rng.random(); pn=pname[x,z]
    plant=pn!='' and gt[x,z]-1<=Hp[x,z]<=gt[x,z]+4
    soil=t in ('grass_block','moss_block','podzol','rooted_dirt','dirt','coarse_dirt','pale_moss_block','mud','packed_mud','mycelium')
    if not soil: 
        if r<0.01 and t in ('gravel','stone','andesite','tuff','cobblestone'): put(x,z,y,'stone_button' if not DIRE[x,z] else 'polished_blackstone_button',face='floor',facing=HORZ[int(rng.integers(4))],powered='false')
        continue
    if plant and pn.startswith('flowers_'):
        if r<0.55:
            c=Cp[x,z][None]
            if rng.random()<0.25: put(x,z,y,'wildflowers',facing=HORZ[int(rng.integers(4))],flower_amount=int(rng.integers(1,5)))
            else: put(x,z,y,FLW[int(nearest(c,FLW,'flower',1.0,20)[0])])
        elif r<0.8: put(x,z,y,'short_grass')
        continue
    if plant and pn.startswith('petals_pink'): put(x,z,y,'pink_petals',facing=HORZ[int(rng.integers(4))],flower_amount=int(rng.integers(1,5))); continue
    if plant and pn.startswith('mushrooms'):
        if r<0.6: put(x,z,y,'red_mushroom' if rng.random()<0.5 else 'brown_mushroom')
        continue
    if plant and pn.startswith('grass_clump_00a_brown'):
        if r<0.5: put(x,z,y,'short_dry_grass')
        elif r<0.7: put(x,z,y,'tall_dry_grass')
        continue
    if plant and pn.startswith(('plants001','fountain_of_life_plants','grass_clump')):
        if r<0.3: put(x,z,y,'fern')
        elif r<0.5: tall(x,z,y,'large_fern')
        elif r<0.65: put(x,z,y,'bush')
        elif r<0.8: put(x,z,y,'short_grass')
        continue
    if DIRE[x,z]:
        if canopy[x,z]:
            if r<0.25: put(x,z,y,'pale_moss_carpet',bottom='true',east='none',north='none',south='none',west='none')
            elif r<0.40: put(x,z,y,'leaf_litter',facing=HORZ[int(rng.integers(4))],segment_amount=int(rng.integers(1,5)))
            elif r<0.43: put(x,z,y,'brown_mushroom')
            elif r<0.45: put(x,z,y,'dead_bush')
        else:
            if r<0.10: put(x,z,y,'short_dry_grass')
            elif r<0.14: put(x,z,y,'tall_dry_grass')
            elif r<0.16: put(x,z,y,'dead_bush')
            elif r<0.165: put(x,z,y,'brown_mushroom')
            elif r<0.17: put(x,z,y,'polished_blackstone_button',face='floor',facing=HORZ[int(rng.integers(4))],powered='false')
    else:
        if canopy[x,z]:
            if r<0.25: put(x,z,y,'leaf_litter',facing=HORZ[int(rng.integers(4))],segment_amount=int(rng.integers(1,5)))
            elif r<0.33: put(x,z,y,'fern')
            elif r<0.37: put(x,z,y,'moss_carpet')
            elif r<0.39: tall(x,z,y,'large_fern')
            elif r<0.40: put(x,z,y,'red_mushroom' if rng.random()<0.4 else 'brown_mushroom')
            elif r<0.42: put(x,z,y,'bush')
        else:
            if t!='grass_block':
                if r<0.08: put(x,z,y,'short_grass')
                continue
            if r<0.28: put(x,z,y,'short_grass')
            elif r<0.33: tall(x,z,y,'tall_grass')
            elif r<0.35: put(x,z,y,'fern')
            elif r<0.365: put(x,z,y,'bush')
            elif r<0.375: put(x,z,y,'wildflowers',facing=HORZ[int(rng.integers(4))],flower_amount=int(rng.integers(1,5)))
            elif r<0.38: put(x,z,y,FLW[int(rng.integers(len(FLW)))])
            elif r<0.395 and nearwater[x,z]: put(x,z,y,'firefly_bush')
print('veg',stats,time.time()-T,flush=True)
# ---------- water plants -------------
wx,wz=np.nonzero(water)
for x,z in zip(wx,wz):
    s=wl[x,z]; d=s-gt[x,z]; r=rng.random(); pn=pname[x,z]
    lily=pn.startswith(('lily','water_creep_camp_lily')) and abs(Hp[x,z]-s)<3
    if (lily and r<0.6) or r<0.01:
        if air(x,z,s+1): put(x,z,s+1,'lily_pad'); continue
    if d>=3 and r<0.12: put(x,z,gt[x,z]+1,'tall_seagrass',half='lower'); put(x,z,gt[x,z]+2,'tall_seagrass',half='upper')
    elif d>=2 and r<0.3: put(x,z,gt[x,z]+1,'seagrass')
    elif d>=2 and r<0.33: put(x,z,gt[x,z]+1,'sea_pickle',pickles=int(rng.integers(1,5)),waterlogged='true')
print('water plants',time.time()-T,flush=True)
# ---------- fence / wall connections -------------
names=np.array([s.split('[')[0].split(':')[1] for s in pal],object)
isF=np.array([n.endswith('_fence') for n in names]); isW=np.array([n.endswith('_wall') for n in names])
nonsolid=np.array([n.endswith(('_button','_fence','_wall','grass','fern','flower','flowers','bush','mushroom','_vines','vines_plant','moss','carpet','litter','petals','lantern','torch','candle','iron_chain','vine','seagrass','sea_pickle','lily_pad','spore_blossom','hanging_roots','pot','_shelf'))
     or n in ('air','water','lava','poppy','dandelion','cornflower','oxeye_daisy','azure_bluet','allium','blue_orchid','lily_of_the_valley','torchflower','dead_bush') or '_tulip' in n for n in names])
NP=4096
connF=np.zeros(NP,bool); connF[:len(pal)]=~nonsolid|isF
connW=np.zeros(NP,bool); connW[:len(pal)]=~nonsolid|isW
isF=np.pad(isF,(0,NP-len(isF))); isW=np.pad(isW,(0,NP-len(isW)))
fx,fz,fy=np.nonzero((isF|isW)[B])
for x,z,y in zip(fx,fz,fy):
    n=pal[B[x,z,y]].split('[')[0].split(':')[1]; w=isW[B[x,z,y]]; cn=connW if w else connF
    pr={}
    for d,dx,dz in DIRS:
        a,b=x+dx,z+dz
        c=0<=a<NX and 0<=b<NZ and cn[B[a,b,y]]
        pr[d]=('low' if c else 'none') if w else str(c).lower()
    if w:
        up=not(pr['east']==pr['west']=='low' and pr['north']==pr['south']=='none') and not(pr['north']==pr['south']=='low' and pr['east']==pr['west']=='none')
        pr['up']=str(up or B[x,z,y+1]!=0).lower()
    k=P(n,waterlogged='false',**pr); isF[k]=connF[k]=not w; isW[k]=connW[k]=w
print('connections',len(fx),time.time()-T,flush=True)
np.save(D+'B_final.npy',B); json.dump(pal,open(D+'pal_final.json','w'))
print('DONE',len(pal),(B>0).sum(),time.time()-T)

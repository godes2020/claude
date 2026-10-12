# Build a textured mesh of the litematic grid for Blender rendering.
import numpy as np, json, os, time, sys
from PIL import Image
T=time.time(); D='/home/user/dota_work/mc/'; TX=D+'npm/mca/package/minecraft-assets/data/1.21.11/blocks/'
B=np.load(D+'B_final.npy'); pal=json.load(open(D+'pal_final.json'))
NX,NZ,NY=B.shape
def parse(s):
    n=s.split('[')[0].split(':')[1]; pr=dict(p.split('=') for p in s[s.index('[')+1:-1].split(',')) if '[' in s else {}
    return n,pr
PS=[parse(s) for s in pal]
GRASS=(145,189,89); FOL=(119,171,47); SPR=(97,153,97); BIR=(128,167,85); MANG=(141,177,39); WAT=(63,118,228)
TINT={'grass_block_top':GRASS,'short_grass':GRASS,'tall_grass_top':GRASS,'tall_grass_bottom':GRASS,'fern':GRASS,'large_fern_top':GRASS,'large_fern_bottom':GRASS,'bush':GRASS,
 'oak_leaves':FOL,'jungle_leaves':FOL,'acacia_leaves':FOL,'dark_oak_leaves':FOL,'vine':FOL,'mangrove_leaves':MANG,'spruce_leaves':SPR,'birch_leaves':BIR,'lily_pad':(32,128,48),'water_still':WAT,'leaf_litter':(160,110,60)}
FILES=set(f[:-4] for f in os.listdir(TX) if f.endswith('.png'))
tiles=[]; tid={}
ALIAS={'moss_carpet':'moss_block','pale_moss_carpet':'pale_moss_carpet','candle_lit':'candle_lit'}
def tile(name,opaque=False):
    name=ALIAS.get(name,name)
    if name not in FILES: name='stone'
    k=(name,opaque)
    if k in tid: return tid[k]
    im=Image.open(TX+name+'.png').convert('RGBA'); w=im.size[0]; im=im.crop((0,0,w,w)).resize((16,16),Image.NEAREST)
    a=np.array(im).astype(np.float32)
    if name in TINT: a[...,:3]*=np.array(TINT[name],np.float32)/255
    if opaque:
        m=a[...,3:4]/255; avg=(a[...,:3]*m).sum((0,1))/max(m.sum(),1); a[...,:3]=a[...,:3]*m+avg*0.55*(1-m); a[...,3]=255
    tid[k]=len(tiles); tiles.append(a.clip(0,255).astype(np.uint8)); return tid[k]
def base_of(n):
    for suf in ('_stairs','_wall','_fence','_button','_slab','_pressure_plate'):
        if n.endswith(suf):
            b=n[:-len(suf)]
            for c in (b,b+'s',b+'_planks',b.replace('brick','bricks'),b.replace('tile','tiles'),b+'_block'):
                if c in FILES: return c
            if b=='stone_brick': return 'stone_bricks'
            if b=='polished_blackstone_brick': return 'polished_blackstone_bricks'
            return 'stone'
    return n
def tex3(n):
    """top, side, bottom texture names for a full block"""
    n=base_of(n)
    if n.endswith('_log') or n=='bamboo_block': return n+'_top',n,n+'_top'
    if n in ('basalt','polished_basalt'): return n+'_top',n+'_side',n+'_top'
    if n=='grass_block': return 'grass_block_top','grass_block_side','dirt'
    if n in ('podzol','mycelium','muddy_mangrove_roots'): return n+'_top',n+'_side','dirt' if n!='muddy_mangrove_roots' else n+'_top'
    if n=='magma_block': return 'magma','magma','magma'
    if n=='barrel': return 'barrel_top','barrel_side','barrel_bottom'
    if n in ('water','lava'): return n+'_still',n+'_still',n+'_still'
    if n=='smooth_stone': return 'smooth_stone','smooth_stone_slab_side','smooth_stone'
    t=n+'_top' if n+'_top' in FILES else n; s=n+'_side' if n+'_side' in FILES else n; b=n+'_bottom' if n+'_bottom' in FILES else t
    for x in (t,s,b):
        if x not in FILES: return ('stone',)*3
    return t,s,b
CROSS={'short_grass','fern','bush','firefly_bush','dead_bush','short_dry_grass','tall_dry_grass','red_mushroom','brown_mushroom','seagrass','cave_vines','cave_vines_plant','pale_hanging_moss','hanging_roots','copper_torch','soul_torch','iron_chain','sea_pickle','spore_blossom',
 'poppy','dandelion','cornflower','oxeye_daisy','azure_bluet','allium','blue_orchid','red_tulip','orange_tulip','pink_tulip','white_tulip','lily_of_the_valley','torchflower'}
TALL={'tall_grass','large_fern','tall_seagrass'}
FLAT={'leaf_litter','pink_petals','wildflowers','moss_carpet','pale_moss_carpet','lily_pad'}
# classify palette
kind=np.zeros(len(pal),np.uint8)  # 0 air 1 full opaque 2 water 3 lava 4 partial
for i,(n,pr) in enumerate(PS):
    if n=='air': continue
    if n=='water': kind[i]=2
    elif n=='lava': kind[i]=3
    elif n in CROSS or n in TALL or n in FLAT or n=='vine' or n.endswith(('_stairs','_wall','_fence','_button','lantern','candle','_shelf','torch')) or n=='decorated_pot': kind[i]=4
    else: kind[i]=1
K=kind[B]
V=[];F=[];UV=[];M=[]  # M: 0 opaque,1 cutout,2 water,3 lava(emissive)
nv=0
# ---------- full cubes, vectorized ----------
full=(K==1)|(K==3)
opq=full
FACES={ # name: (dx,dy,dz) in grid (x,z,y) order -> quad corners in world (x,y=z grid,z=up)
 'top':((0,0,1),[(0,0,1),(1,0,1),(1,1,1),(0,1,1)]),
 'bottom':((0,0,-1),[(0,1,0),(1,1,0),(1,0,0),(0,0,0)]),
 'east':((1,0,0),[(1,0,0),(1,1,0),(1,1,1),(1,0,1)]),
 'west':((-1,0,0),[(0,1,0),(0,0,0),(0,0,1),(0,1,1)]),
 'south':((0,1,0),[(1,1,0),(0,1,0),(0,1,1),(1,1,1)]),
 'north':((0,-1,0),[(0,0,0),(1,0,0),(1,0,1),(0,0,1)]),
}
UVQ=np.array([(0,0),(1,0),(1,1),(0,1)],np.float32)
T3=[tex3(n) if kind[i] in (1,3) else None for i,(n,pr) in enumerate(PS)]
def tile_for(i,face):
    n,pr=PS[i]; t,s,b=T3[i]
    ax=pr.get('axis','y')
    if ax!='y' and (n.endswith('_log') or n in ('bamboo_block','basalt','polished_basalt','deepslate')):
        endf={'x':('east','west'),'z':('north','south')}[ax]
        name=t if face in endf else s
    else: name=t if face=='top' else (b if face=='bottom' else s)
    return tile(name,opaque=('leaves' in name or n=='moss_block'))
tilemap={}
pad=np.zeros((NX+2,NZ+2,NY+2),bool); pad[1:-1,1:-1,1:-1]=opq
fx,fz,fy=np.nonzero(full)
bid=B[fx,fz,fy]
for face,((dx,dz,dy),corn) in FACES.items():
    exp=~pad[fx+1+dx,fz+1+dz,fy+1+dy]
    if face=='bottom': exp&=fy>0
    x,z,y,b=fx[exp],fz[exp],fy[exp],bid[exp]
    ub,inv=np.unique(b,return_inverse=True)
    t=np.array([tile_for(i,face) for i in ub],np.int32)[inv]
    n=len(x); c=np.array(corn,np.float32)
    v=np.stack([x,z,y],1)[:,None,:].astype(np.float32)+c[None]  # (n,4,3) in (x,z,y)
    V.append(v.reshape(-1,3)); F.append(nv+np.arange(n*4).reshape(n,4)); nv+=n*4
    UV.append(np.tile(UVQ,(n,1))); M.append(np.where(kind[b]==3,3,0).astype(np.uint8))
    tilemap.setdefault('t',[]).append(t)
    print(face,n,flush=True)
# ---------- water surfaces ----------
wx,wz,wy=np.nonzero(K==2)
up=K[wx,wz,np.minimum(wy+1,NY-1)]
for face,((dx,dz,dy),corn) in FACES.items():
    nk=K[np.clip(wx+dx,0,NX-1),np.clip(wz+dz,0,NZ-1),np.clip(wy+dy,0,NY-1)]
    exp=(nk==0)|(nk==4)
    if face=='top': pass
    x,z,y=wx[exp],wz[exp],wy[exp]; n=len(x)
    c=np.array(corn,np.float32); 
    if face=='top': c[:,2]=0.875
    v=np.stack([x,z,y],1)[:,None,:].astype(np.float32)+c[None]
    V.append(v.reshape(-1,3)); F.append(nv+np.arange(n*4).reshape(n,4)); nv+=n*4
    UV.append(np.tile(UVQ,(n,1))); M.append(np.full(n,2,np.uint8)); tilemap['t'].append(np.full(n,tile('water_still'),np.int32))
print('full+water faces',sum(len(f) for f in F),time.time()-T,flush=True)
# ---------- partial blocks ----------
pv=[];pf=[];puv=[];pm=[];pt=[]
def quad(p4,uv4,t,m=1):
    global nv
    pv.extend(p4); puv.extend(uv4); pf.append([nv,nv+1,nv+2,nv+3]); nv+=4; pt.append(t); pm.append(m)
def box(x,z,y,x0,x1,z0,z1,y0,y1,tt,ts=None,m=0):
    ts=tt if ts is None else ts
    X0,X1,Z0,Z1,Y0,Y1=x+x0,x+x1,z+z0,z+z1,y+y0,y+y1
    quad([(X0,Z0,Y1),(X1,Z0,Y1),(X1,Z1,Y1),(X0,Z1,Y1)],[(x0,z0),(x1,z0),(x1,z1),(x0,z1)],tt,m)
    quad([(X0,Z1,Y0),(X1,Z1,Y0),(X1,Z0,Y0),(X0,Z0,Y0)],[(x0,z0),(x1,z0),(x1,z1),(x0,z1)],tt,m)
    for a,b_,u0,u1 in (((X1,Z0),(X1,Z1),z0,z1),((X0,Z1),(X0,Z0),z0,z1),((X1,Z1),(X0,Z1),x0,x1),((X0,Z0),(X1,Z0),x0,x1)):
        quad([(a[0],a[1],Y0),(b_[0],b_[1],Y0),(b_[0],b_[1],Y1),(a[0],a[1],Y1)],[(u0,y0),(u1,y0),(u1,y1),(u0,y1)],ts,m)
def cross(x,z,y,t,h=1.0,y0=0.0):
    for (a,b_) in (((0.15,0.15),(0.85,0.85)),((0.15,0.85),(0.85,0.15))):
        quad([(x+a[0],z+a[1],y+y0),(x+b_[0],z+b_[1],y+y0),(x+b_[0],z+b_[1],y+y0+h),(x+a[0],z+a[1],y+y0+h)],[(0,0),(1,0),(1,h),(0,h)],t,1)
def flat(x,z,y,t,h=0.03):
    quad([(x,z,y+h),(x+1,z,y+h),(x+1,z+1,y+h),(x,z+1,y+h)],[(0,0),(1,0),(1,1),(0,1)],t,1)
px,pz,py=np.nonzero(K==4)
DIR={'east':(1,0),'west':(-1,0),'south':(0,1),'north':(0,-1)}
for x,z,y in zip(px,pz,py):
    n,pr=PS[B[x,z,y]]
    if n in CROSS:
        tn={'cave_vines':'cave_vines_lit' if pr.get('berries')=='true' else 'cave_vines','cave_vines_plant':'cave_vines_plant_lit' if pr.get('berries')=='true' else 'cave_vines_plant','pale_hanging_moss':'pale_hanging_moss_tip' if pr.get('tip')=='true' else 'pale_hanging_moss'}.get(n,n)
        if n=='spore_blossom': flat(x,z,y,tile('spore_blossom'),0.97); continue
        cross(x,z,y,tile(tn),0.8 if n in('sea_pickle','red_mushroom','brown_mushroom') else 1.0)
    elif n in TALL: cross(x,z,y,tile(n+('_top' if pr['half']=='upper' else '_bottom')))
    elif n in FLAT: flat(x,z,y,tile(n),0.02 if n!='lily_pad' else 0.06)
    elif n=='vine':
        t=tile('vine')
        for d,(dx,dz) in DIR.items():
            if pr.get(d)=='true':
                xo=x+(0.97 if dx>0 else 0.03) if dx else None
                if dx: quad([(xo,z,y),(xo,z+1,y),(xo,z+1,y+1),(xo,z,y+1)],[(0,0),(1,0),(1,1),(0,1)],t,1)
                else:
                    zo=z+(0.97 if dz>0 else 0.03); quad([(x,zo,y),(x+1,zo,y),(x+1,zo,y+1),(x,zo,y+1)],[(0,0),(1,0),(1,1),(0,1)],t,1)
    elif n.endswith('_fence') or n.endswith('_wall'):
        w=n.endswith('_wall'); t=tile(base_of(n)); r=0.25 if w else 0.375; ar=0.3125 if w else 0.4375
        box(x,z,y,r,1-r,r,1-r,0,1,t)
        for d,(dx,dz) in DIR.items():
            v=pr.get(d,'false')
            if v in ('true','low','tall'):
                h=(0.8125 if w else 0.9375)
                if dx: box(x,z,y,0.5 if dx>0 else 0,1 if dx>0 else 0.5,ar,1-ar,0 if w else 0.375,h,t)
                else: box(x,z,y,ar,1-ar,0.5 if dz>0 else 0,1 if dz>0 else 0.5,0 if w else 0.375,h,t)
    elif n.endswith('_stairs'):
        tt,ts,_=tex3(base_of(n)); t1,t2=tile(tt),tile(ts)
        box(x,z,y,0,1,0,1,0,0.5,t1,t2)
        dx,dz=DIR[pr['facing']]
        if dx: box(x,z,y,0.5 if dx>0 else 0,1 if dx>0 else 0.5,0,1,0.5,1,t1,t2)
        else: box(x,z,y,0,1,0.5 if dz>0 else 0,1 if dz>0 else 0.5,0.5,1,t1,t2)
    elif n.endswith('_button'):
        t=tile(base_of(n))
        if pr['face']=='floor': box(x,z,y,0.31,0.69,0.37,0.63,0,0.125,t)
        else:
            dx,dz=DIR[pr['facing']]
            if dx: box(x,z,y,0 if dx>0 else 0.875,0.125 if dx>0 else 1,0.31,0.69,0.37,0.63,t)
            else: box(x,z,y,0.31,0.69,0 if dz>0 else 0.875,0.125 if dz>0 else 1,0.37,0.63,t)
    elif n.endswith('lantern'):
        t=tile(n); y0=0.0625 if pr.get('hanging')=='true' else 0
        box(x,z,y,0.3125,0.6875,0.3125,0.6875,y0,y0+0.5,t,m=4)
    elif n.endswith('torch'): cross(x,z,y,tile(n),0.75)
    elif n=='candle': box(x,z,y,0.44,0.56,0.44,0.56,0,0.4,tile('candle_lit'),m=4)
    elif n.endswith('_shelf'): box(x,z,y,0,1,0,1,0,1,tile(n.replace('_shelf','_planks')),tile(n))
    elif n=='decorated_pot': box(x,z,y,0.0625,0.9375,0.0625,0.9375,0,1,tile('terracotta'),tile('decorated_pot_side') if 'decorated_pot_side' in FILES else tile('terracotta'))
    else: box(x,z,y,0,1,0,1,0,1,tile('stone'))
print('partial quads',len(pf),time.time()-T,flush=True)
V.append(np.array(pv,np.float32).reshape(-1,3)); F.append(np.array(pf,np.int64).reshape(-1,4)); UV.append(np.array(puv,np.float32).reshape(-1,2)); M.append(np.array(pm,np.uint8)); tilemap['t'].append(np.array(pt,np.int32))
V=np.concatenate(V); F=np.concatenate(F); UV=np.concatenate(UV); M=np.concatenate(M); TL=np.concatenate(tilemap['t'])
# atlas
NT=len(tiles); AW=int(np.ceil(np.sqrt(NT))); atlas=np.zeros((AW*16,AW*16,4),np.uint8)
for i,t in enumerate(tiles): r,c=divmod(i,AW); atlas[r*16:(r+1)*16,c*16:(c+1)*16]=t
Image.fromarray(atlas).save(D+'rend/atlas.png')  # flipped so v=0 at bottom row in blender
# convert per-loop UVs into atlas coords. local uv (u,v) in 0..1, v measured from bottom of tile (image row 15)
tl=np.repeat(TL,4); r,c=np.divmod(tl,AW)
eps=0.02
u=np.clip(UV[:,0],eps,1-eps); v=np.clip(UV[:,1],eps,1-eps)
# image row r stored top-down; after flip, tile row r occupies blender v in [(AW-1-r)/AW,(AW-r)/AW]
AU=(c+u)/AW; AV=(AW-1-r+v)/AW
# world coords: blender X = grid x, Y = -grid z (so north is +Y), Z = up
VW=np.stack([V[:,0],-V[:,1],V[:,2]],1)
np.savez(D+'rend/mesh.npz',V=VW.astype(np.float32),F=F.astype(np.int32),UV=np.stack([AU,AV],1).astype(np.float32),M=M)
print('verts',len(V),'faces',len(F),'tiles',NT,time.time()-T)

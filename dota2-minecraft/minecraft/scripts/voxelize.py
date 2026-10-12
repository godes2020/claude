import numpy as np, json, time, sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
T=time.time()
D='/home/user/dota_work/mc/'
import os
S=float(os.environ.get('S','1.85')); OD=os.environ.get('OD',D); os.makedirs(OD,exist_ok=True); XMAX=268.7; YMAX=257.1; ZMIN=-12.0
X=np.load(D+'xyz.npy',mmap_mode='r'); UVA=np.load(D+'uv.npy',mmap_mode='r'); MA=np.load(D+'mat.npy'); TOM=np.load(D+'tree_obj_mask.npy')[np.load(D+'obj.npy')]; meta=json.load(open(D+'meta.json'))
mats=meta['mats']; NM=len(mats)
NX=int((YMAX+259.0)*S)+2; NZ=int((XMAX+273.2)*S)+2; NY=int((48-ZMIN)*S)+2+int(6*S/1.85)
print('GRID',NX,NY,NZ)
def cat(n):
    n=n.lower()
    if n.startswith(('water_generic','riverflow','water_edges','water_flow','waterfall_mod','waterfall_00','fountain_waterfall')): return 'water'
    if n.startswith(('dire_lava','bad_puddle_lava')): return 'lava'
    if n.startswith(('mod_','cliff_wall','ground_rock','rock_forest_04')): return 'ground'
    if n.startswith(('path_border','wagon_path','ground_edge','camp_marking','blood','xp_shrine_ground','ti01','stone_path009','tile_stone','good_base_stone','bad_base_stone','bad_ancient_temp','wardspot','logo_plate','fountain_of_life_algae','camp_fire_pit')): return 'decal'
    if n.startswith(('flowers_','plants001','grass_clump','mushrooms_wild','lily_pad','lily_flower','water_creep_camp_lily','petals_pink','fountain_of_life_plants')): return 'plant'
    if n.startswith(('tree_','dire_tree','roots_radiant','roots_outpost','radiant_ancient_tree','team_portal_base_radiant_tree')): return 'tree'
    if n.startswith('universal_vines'): return 'vine'
    return 'build'
CATS=[cat(m['name']) for m in mats]
# tint table (same as render)
TINT=[('mod_radiant_path_destruction',(0.62,0.56,0.45)),('mod_radiant_dire',(1.0,1.0,1.0)),('mod_radiant',(0.27,0.46,0.12)),
 ('mod_dire',(0.24,0.20,0.165)),('cliff_wall',(0.62,0.58,0.50)),('ground_rock',(0.62,0.58,0.50)),('river_rocks',(0.70,0.68,0.62)),
 ('grass_clump_tintable',('POS',(0.5,0.85,0.25),(0.36,0.30,0.22))),('path_border_tint',('POS',(0.62,0.6,0.40),(0.36,0.30,0.24))),
 ('wagon_path_tintable',('POS',(0.66,0.58,0.40),(0.36,0.30,0.24))),('ground_edge001_tintable',('POS',(0.45,0.6,0.25),(0.34,0.29,0.22))),
 ('petals_pink001',(1.0,0.55,0.72)),('wood_fence001_tintable',(0.75,0.58,0.40)),('campfire_rocks',(0.8,0.78,0.72)),('statue001',(0.85,0.82,0.75)),
 ('tree_oak_leaves_blank',(0.30,0.50,0.15)),('fountain_radiant_00',(0.6,0.9,1.0))]
def tintof(n):
    n=n.lower()
    for k,s in TINT:
        if n.startswith(k): return s
    return None
TN=[tintof(m['name']) for m in mats]
imgs={}
def load(p,alpha=False):
    key=(p,alpha)
    if key not in imgs:
        try:
            im=Image.open(p)
            if alpha: a=np.asarray(im.convert('RGBA'))[:,:,3] if im.mode in('RGBA','LA','PA') or 'A' in im.getbands() else np.asarray(im.convert('L'))
            else: a=np.asarray(im.convert('RGB'))
            imgs[key]=a
        except Exception as e:
            print('IMGFAIL',p,e); imgs[key]=None
    return imgs[key]
def sample(a,u,v):
    H,W=a.shape[:2]
    x=((u%1.0)*W).astype(np.int32)%W; y=(((1.0-v)%1.0)*H).astype(np.int32)%H
    return a[y,x]
rng=np.random.default_rng(1)
area=0.5*np.linalg.norm(np.cross(X[:,1]-X[:,0],X[:,2]-X[:,0]),axis=1)
DENS=float(os.environ.get('DENS','6.0'))
K=np.clip(np.ceil(area*S*S*DENS),1,80000).astype(np.int64); K[TOM]=0
print('SAMPLES',K.sum(),time.time()-T)
CH=400000
OUT={c:[] for c in ('vox','decal','plant','water')}
CI={'ground':4,'lava':5,'leaves':6,'wood':7,'build':8,'vine':3}
for s0 in range(0,len(X),CH):
    s1=min(len(X),s0+CH)
    k=K[s0:s1]; ti=np.repeat(np.arange(s0,s1),k)
    r1=rng.random(len(ti),dtype=np.float32); r2=rng.random(len(ti),dtype=np.float32)
    f=r1+r2>1; r1[f]=1-r1[f]; r2[f]=1-r2[f]
    one=np.repeat(k==1,k); r1[one]=1/3; r2[one]=1/3
    tx=np.asarray(X[s0:s1]); tu=np.asarray(UVA[s0:s1]); li=ti-s0
    a,b,c=tx[li,0],tx[li,1],tx[li,2]
    P=a+r1[:,None]*(b-a)+r2[:,None]*(c-a)
    ua,ub,uc=tu[li,0],tu[li,1],tu[li,2]
    U=ua+r1[:,None]*(ub-ua)+r2[:,None]*(uc-ua)
    m=MA[ti]
    rgb=np.zeros((len(ti),3),np.float32); al=np.ones(len(ti),np.float32)
    for mi in np.unique(m):
        sel=np.nonzero(m==mi)[0]; md=mats[mi]
        if 'img' in md:
            im=load(md['img'])
            if im is not None: rgb[sel]=sample(im,U[sel,0],U[sel,1])/255.0
            else: rgb[sel]=0.5
        else: rgb[sel]=md.get('col',[0.5]*3)
        if 'aimg' in md:
            aa=load(md['aimg'],md.get('asock')=='Alpha')
            if aa is not None: al[sel]=sample(aa,U[sel,0],U[sel,1])/255.0
        t=TN[mi]
        if t is not None:
            if t[0]=='POS':
                fac=np.clip(((P[sel,0]-P[sel,1])+40)/80,0,1)[:,None]
                tc=np.array(t[1])*(1-fac)+np.array(t[2])*fac
            else: tc=np.array(t)
            rgb[sel]*=tc
    # per-triangle mean alpha -> wood vs leaves for tree mats
    tri_al=np.bincount(li,al,minlength=s1-s0)/np.maximum(np.bincount(li,minlength=s1-s0),1)
    ok=al>0.5
    cats=np.array([CATS[i] for i in range(NM)])[m]
    # grid coords
    gx=((YMAX-P[:,1])*S).astype(np.int32); gz=((XMAX-P[:,0])*S).astype(np.int32); gyf=(P[:,2]-ZMIN)*S
    gy=np.clip(gyf.astype(np.int32),0,NY-1)
    col=(gx.astype(np.int64)*NZ+gz)
    rgb8=(np.clip(rgb,0,1)*255).astype(np.uint8)
    for cn in ('decal','plant','water'):
        s=(cats==cn)&ok
        if s.any(): OUT[cn].append((col[s],gyf[s].astype(np.float32),rgb8[s],m[s]))
    ci=np.zeros(len(ti),np.uint8)
    for cn,v in CI.items(): ci[cats==cn]=v
    tr=cats=='tree'
    ci[tr]=np.where(tri_al[li[tr]]>0.97,CI['wood'],CI['leaves'])
    s=(ci>0)&ok
    idx=(col*NY+gy)
    OUT['vox'].append((idx[s],ci[s],rgb8[s],m[s]))
    print('chunk',s0,len(ti),time.time()-T,flush=True)
for kname,lst in OUT.items():
    arrs=[np.concatenate([l[i] for l in lst]) for i in range(4)]
    np.savez(OD+f'raw_{kname}.npz',a=arrs[0],b=arrs[1],c=arrs[2],m=arrs[3])
    print('SAVED',kname,len(arrs[0]))
json.dump({'NX':NX,'NY':NY,'NZ':NZ,'S':S,'XMAX':XMAX,'YMAX':YMAX,'ZMIN':ZMIN,'CATS':CATS,'CI':CI},open(OD+'grid.json','w'))
print('DONE',time.time()-T)

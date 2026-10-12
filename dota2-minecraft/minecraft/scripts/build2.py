import numpy as np, json, time
from scipy import ndimage as ndi
import os
T=time.time(); D='/home/user/dota_work/mc/'; OD=os.environ['OD']
meta=json.load(open(D+'meta.json')); MN=[m['name'].lower() for m in meta['mats']]
PAL=json.load(open(D+'palette.json'))
CAT=np.load(OD+'CAT.npy',mmap_mode='r'); COL=np.load(OD+'COL.npy',mmap_mode='r'); MAT=np.load(OD+'MAT.npy',mmap_mode='r')
B=np.load(OD+'B_stage1.npy'); pal=json.load(open(OD+'pal_stage1.json')); pid={s:i for i,s in enumerate(pal)}
NX,NZ,NY=B.shape
G=json.load(open(OD+'grid.json')); S,XMAX,YMAX=G['S'],G['XMAX'],G['YMAX']; F=S/1.85
SG=np.load(OD+'stage_ground.npz'); gt,inside,water,wl,DIRE=SG['gt'],SG['inside'],SG['water'],SG['wl'],SG['DIRE']
SPJ=json.load(open(OD+'special.json')); _ii,_jj=np.indices((NX,NZ)); SPECIAL_ZONE=np.zeros((NX,NZ),bool)
for k_,r_ in (('lotus',27),('shrine',16)):
    for cx_,cz_ in SPJ[k_]: SPECIAL_ZONE|=(_ii-cx_)**2+(_jj-cz_)**2<=r_*r_
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

# ================= procedural natural trees =================
air=lambda x,z,y: 0<=x<NX and 0<=z<NZ and 0<=y<NY and B[x,z,y]==0
DIRS=[('east',1,0),('west',-1,0),('south',0,1),('north',0,-1)]
LEAFIDS=set()
def LPi(n):
    k=LP(n); LEAFIDS.add(k); return k
CAN=np.zeros((NX,NZ),bool)
def put_leaves(xs,zs,ys,names,probs):
    ok=(xs>=0)&(xs<NX)&(zs>=0)&(zs<NZ)&(ys>=0)&(ys<NY)
    xs,zs,ys=xs[ok],zs[ok],ys[ok]
    cur=B[xs,zs,ys]; free=cur==0
    xs,zs,ys=xs[free],zs[free],ys[free]
    ids=np.array([LPi(n) for n in names],np.uint16)
    B[xs,zs,ys]=ids[rng.choice(len(ids),len(xs),p=np.array(probs)/sum(probs))]
    CAN[xs,zs]=True
    return xs,zs,ys
def blob(cx,cz,cy,rx,ry,names,probs,rough=0.35,rz=None):
    rz=rx if rz is None else rz
    R=int(np.ceil(max(rx,rz)))+1; Ry=int(np.ceil(ry))+1
    gx,gz,gy=np.mgrid[-R:R+1,-R:R+1,-Ry:Ry+1]
    d=(gx/rx)**2+(gz/rz)**2+(gy/ry)**2
    keep=d<=1-rough*rng.random(d.shape)
    return put_leaves(gx[keep]+int(round(cx)),gz[keep]+int(round(cz)),gy[keep]+int(round(cy)),names,probs)
def setlog(x,z,y,name,axis='y',force=False):
    if 0<=x<NX and 0<=z<NZ and 0<=y<NY and (force or B[x,z,y]==0 or B[x,z,y] in LEAFIDS):
        B[x,z,y]=P(name,axis=axis); return True
    return False
def line(p0,p1,name,th=1):
    p0=np.array(p0,float); p1=np.array(p1,float); d=p1-p0; n=int(np.ceil(np.abs(d).max()*1.5))+1
    ax=['x','z','y'][int(np.argmax(np.abs(d)))]
    for t in np.linspace(0,1,n):
        q=p0+d*t
        for a in range(th):
            for b in range(th):
                setlog(int(round(q[0]))+a,int(round(q[1]))+b,int(round(q[2])),name,ax)
FENCE={'crimson_stem':'crimson_fence','oak_log':'oak_fence','spruce_log':'spruce_fence','dark_oak_log':'dark_oak_fence','pale_oak_log':'pale_oak_fence','cherry_log':'cherry_fence','birch_log':'birch_fence','mangrove_log':'mangrove_fence'}
BUTTON={'crimson_stem':'crimson_button','oak_log':'oak_button','spruce_log':'spruce_button','dark_oak_log':'dark_oak_button','pale_oak_log':'pale_oak_button','cherry_log':'cherry_button','birch_log':'birch_button','mangrove_log':'mangrove_button'}
def fence(x,z,y,log):
    if air(x,z,y): B[x,z,y]=P(FENCE[log],east='false',north='false',south='false',west='false',waterlogged='false')
def trunk(x,z,y0,y1,log,th=1):
    # extend down to solid ground
    for a in range(th):
        for b in range(th):
            yy=y0-1
            while yy>0 and B[x+a,z+b,yy]==0 and y0-yy<6: setlog(x+a,z+b,yy,log); yy-=1
            for y in range(y0,y1): setlog(x+a,z+b,y,log,force=B[x+a,z+b,y]==0 or B[x+a,z+b,y] in LEAFIDS)
def roots(x,z,y,log,th,n,L):
    for k in rng.permutation(4)[:n]:
        d,dx,dz=DIRS[k]
        ox=x+(th if dx>0 else -1 if dx<0 else int(rng.integers(th)))
        oz=z+(th if dz>0 else -1 if dz<0 else int(rng.integers(th)))
        for i in range(L):
            if not setlog(ox+dx*i,oz+dz*i,y,log,'x' if dx else 'z'): break
            if i==L-1 and air(ox+dx*(i+1),oz+dz*(i+1),y): B[ox+dx*(i+1),oz+dz*(i+1),y]=P(BUTTON[log],face='floor',facing=d,powered='false')
def buttons(x,z,y0,y1,log,th,n):
    for _ in range(n):
        d,dx,dz=DIRS[int(rng.integers(4))]; y=int(rng.integers(y0,max(y0+1,y1)))
        bx=x+(th if dx>0 else -1 if dx<0 else int(rng.integers(th))); bz=z+(th if dz>0 else -1 if dz<0 else int(rng.integers(th)))
        if air(bx,bz,y): B[bx,bz,y]=P(BUTTON[log],face='wall',facing=d,powered='false')
def trunk_vines(x,z,y0,y1,th,p):
    for d,dx,dz in DIRS:
        if rng.random()>p: continue
        opp={'east':'west','west':'east','north':'south','south':'north'}[d]
        bx=x+(th if dx>0 else -1 if dx<0 else int(rng.integers(th))); bz=z+(th if dz>0 else -1 if dz<0 else int(rng.integers(th)))
        top=int(rng.integers(y0+1,max(y0+2,y1)))
        for y in range(top,max(y0,top-int(rng.integers(2,6))),-1):
            if air(bx,bz,y): B[bx,bz,y]=P('vine',**{k:('true' if k==opp else 'false') for k in ('east','west','north','south','up')})
def hang(xs,zs,ys,p,kind,maxlen):
    if len(xs)==0: return
    # bottom leaves of the canopy
    for x,z,y in zip(xs,zs,ys):
        if rng.random()>p or not air(x,z,y-1) or B[x,z,y] not in LEAFIDS: continue
        L=int(rng.integers(1,maxlen+1)); k=0
        while k<L and air(x,z,y-1-k) and y-1-k>gt[x,z]+2: k+=1
        if k==0: continue
        for j in range(1,k+1):
            last=j==k
            if kind=='moss': B[x,z,y-j]=P('pale_hanging_moss',tip='true' if last else 'false')
            elif kind=='cave': B[x,z,y-j]=P('cave_vines',age=int(rng.integers(0,26)),berries=str(rng.random()<0.4).lower()) if last else P('cave_vines_plant',berries=str(rng.random()<0.25).lower())
            elif kind=='roots': B[x,z,y-j]=P('hanging_roots',waterlogged='false'); break
LEAVES={
 'green_r':(['oak_leaves','azalea_leaves','flowering_azalea_leaves','dark_oak_leaves'],[55,20,7,18]),
 'green_d':(['dark_oak_leaves','spruce_leaves','mangrove_leaves'],[60,25,15]),
 'red':(['nether_wart_block','dark_oak_leaves','oak_leaves','shroomlight'],[62,20,13,5]),
 'white':(['cherry_leaves','pale_oak_leaves','birch_leaves','flowering_azalea_leaves'],[35,25,20,20]),
 'magic_white':(['pale_oak_leaves','birch_leaves','cherry_leaves'],[60,25,15]),
 'pink':(['cherry_leaves','flowering_azalea_leaves'],[80,20]),
 'pine':(['spruce_leaves'],[1]),
 'dire_big':(['dark_oak_leaves','pale_oak_leaves','moss_block','mangrove_leaves','spruce_leaves'],[45,20,10,10,15]),
 'dire_small':(['dark_oak_leaves','pale_oak_leaves','nether_wart_block'],[50,35,15]),
 'gnarly':(['pale_oak_leaves','moss_block','dark_oak_leaves'],[70,10,20]),
 'bush_r':(['azalea_leaves','oak_leaves','flowering_azalea_leaves','jungle_leaves'],[40,30,20,10]),
 'bush_d':(['dark_oak_leaves','spruce_leaves','mangrove_leaves','pale_oak_leaves'],[45,25,15,15]),
}
SPEC={
 'spruce':('spruce_log',(['spruce_leaves'],[1])),
 'cherry':('cherry_log',(['cherry_leaves'],[1])),
 'birch':('birch_log',(['birch_leaves'],[1])),
 'oak':('oak_log',(['oak_leaves'],[1])),
 'azalea':('oak_log',(['azalea_leaves','flowering_azalea_leaves'],[65,35])),
 'dark_oak':('dark_oak_log',(['dark_oak_leaves'],[1])),
 'red':('crimson_stem',(['nether_wart_block'],[1])),
}
def species(k,leaf,dire):
    if k=='pine': return 'spruce'
    if k=='oak' and leaf in ('red','white','magic_white','pink'): return 'cherry'
    r=rng.random()
    if dire: return 'red' if r<0.25 else 'dark_oak'
    if k=='bush_r' or k=='bush_d': return 'birch' if r<0.4 else ('azalea' if r<0.75 else 'oak')
    return 'birch' if r<0.5 else ('oak' if r<0.75 else 'azalea')
def petals(x,z,r,n,name='pink_petals'):
    for _ in range(n):
        a=x+int(rng.integers(-r,r+1)); b=z+int(rng.integers(-r,r+1))
        if 0<=a<NX and 0<=b<NZ and not water[a,b]:
            y=gt[a,b]+1
            if air(a,b,y): B[a,b,y]=P(name,facing=DIRS[int(rng.integers(4))][0],**({'flower_amount':int(rng.integers(1,5))} if name!='leaf_litter' else {'segment_amount':int(rng.integers(1,5))}))
def t_pine(x,z,y,h,w,dire):
    H=int(max(8,h*S*1.05)); R=max(2.2,w*S*0.5)
    trunk(x,z,y,y+H-1,'spruce_log')
    yb=int(H*0.22); lay=y+yb; layers=[]
    k=0
    while lay<y+H:
        t=(lay-y-yb)/max(1,H-yb); r=R*(1-t)**1.05+0.6
        hgt=max(1,int(round(1.0*F)))
        layers.append((lay,r,hgt)); lay+=hgt+(1 if r>1.5 else 0)
    for (ly,r,hgt) in layers:
        gx,gz=np.mgrid[-int(r)-1:int(r)+2,-int(r)-1:int(r)+2]
        d=np.sqrt(gx**2+gz**2); keep=d<=r-0.4*rng.random(d.shape)
        for j in range(hgt):
            rr=keep&(d<=r*(1-0.25*j/hgt))
            put_leaves(gx[rr]+x,gz[rr]+z,np.full(rr.sum(),ly+j),*LEAVES['pine'])
        # drooping tips
        tip=(d>r-1.2)&keep&(rng.random(d.shape)<0.35)
        put_leaves(gx[tip]+x,gz[tip]+z,np.full(tip.sum(),ly-1),*LEAVES['pine'])
    put_leaves(np.array([x,x]),np.array([z,z]),np.array([y+H-1,y+H]),*LEAVES['pine'])
    if rng.random()<0.5:  # dead twig under the lowest layer
        d,dx,dz=DIRS[int(rng.integers(4))]; fence(x+dx,z+dz,layers[0][0]-1,'spruce_log')
    buttons(x,z,y+1,y+yb,'spruce_log',1,1)
    petals(x,z,int(R),int(R*R*0.4),'leaf_litter')
def crown(x,z,y,th,H,W,log,leaf,nbr,flat=1.0,thick_br=1):
    tops=[]
    for i in range(nbr):
        a=rng.uniform(0,2*np.pi)+i*2*np.pi/nbr; L=W*rng.uniform(0.28,0.42)
        sy=y+int(th*rng.uniform(0.65,1.0)); ey=sy+L*rng.uniform(0.35,0.8)
        ex=x+np.cos(a)*L; ez=z+np.sin(a)*L
        line((x,z,sy),(ex,ez,ey),log,thick_br)
        tops.append((ex,ez,ey))
        if rng.random()<0.6:  # twig out of the crown
            fx,fz=int(round(x+np.cos(a)*(L+W*0.25))),int(round(z+np.sin(a)*(L+W*0.25)))
            fence(fx,fz,int(ey)+int(rng.integers(-1,2)),log)
    tops.append((x,z,y+th+H*0.12))
    cells=[]
    for (cx,cz,cy) in tops:
        rx=W*rng.uniform(0.22,0.3); ry=max(1.6,rx*0.62*flat)
        cells.append(blob(cx,cz,cy+ry*0.35,rx,ry,*leaf))
    xs=np.concatenate([c[0] for c in cells]); zs=np.concatenate([c[1] for c in cells]); ys=np.concatenate([c[2] for c in cells])
    return xs,zs,ys
def bottoms(xs,zs,ys):
    if len(xs)==0: return xs,zs,ys
    k=xs.astype(np.int64)*NZ+zs; o=np.lexsort((ys,k)); k,xs,zs,ys=k[o],xs[o],zs[o],ys[o]
    f=np.r_[True,k[1:]!=k[:-1]]; return xs[f],zs[f],ys[f]
def t_oak(x,z,y,h,w,sp,dire):
    H=max(7.0,h*S); W=max(5.0,w*S*0.95)
    log,LV=SPEC[sp]
    th_=2 if H>=15 else 1
    tt=int(H*0.42)
    trunk(x,z,y,y+tt+1,log,th_)
    xs,zs,ys=crown(x,z,y,tt,H,W,log,LV,int(rng.integers(3,6)),1.0,1)
    roots(x,z,y,log,th_,int(rng.integers(2,5)),max(1,int(F)))
    buttons(x,z,y+1,y+tt,log,th_,int(rng.integers(1,3)))
    bx,bz,by=bottoms(xs,zs,ys)
    if sp in ('oak','azalea'):
        trunk_vines(x,z,y,y+tt,th_,0.35); hang(bx,bz,by,0.05,'cave',int(3*F))
    elif sp=='dark_oak': hang(bx,bz,by,0.06,'moss',int(3*F))
    if sp=='cherry': petals(x,z,int(W*0.5),int(W*W*0.35))
    else: petals(x,z,int(W*0.45),int(W*W*0.2),'leaf_litter')
def t_dire_small(x,z,y,h,w,sp):
    H=max(7.0,h*S*0.95); log,LV=SPEC[sp]
    k=int(H*0.45); dx,dz=DIRS[int(rng.integers(4))][1:]
    trunk(x,z,y,y+k,log); trunk(x+dx,z+dz,y+k,y+int(H*0.8),log)
    tx,tz=x+dx,z+dz; leaves=[]
    for i in range(int(rng.integers(3,6))):
        a=rng.uniform(0,2*np.pi); L=max(2.0,w*S*rng.uniform(0.3,0.5)); sy=y+int(H*rng.uniform(0.45,0.8))
        ex,ez=tx+np.cos(a)*L*0.5,tz+np.sin(a)*L*0.5
        line((tx,tz,sy),(ex,ez,sy+L*0.4),log)
        # fence twig continuing outward and up
        fx,fz=int(round(tx+np.cos(a)*L)),int(round(tz+np.sin(a)*L)); fy=int(sy+L*0.6)
        fence(fx,fz,fy,log); fence(fx,fz,fy+1,log)
        if rng.random()<0.65: leaves.append(blob(fx,fz,fy+1,max(1.2,0.6*F),max(1.0,0.5*F),*LV,rough=0.5))
    roots(x,z,y,log,1,int(rng.integers(1,4)),1)
    buttons(x,z,y+1,y+k,log,1,1)
    if leaves:
        xs=np.concatenate([c[0] for c in leaves]); zs=np.concatenate([c[1] for c in leaves]); ys=np.concatenate([c[2] for c in leaves])
        hang(*bottoms(xs,zs,ys),0.35,'moss',int(4*F))
    petals(x,z,2,4,'leaf_litter')
def t_big(x,z,y,h,w,kind,sp):
    H=max(10.0,h*S); W=max(7.0,w*S*0.95)
    log,LV=SPEC[sp]
    th_=2 if (S>=3 or kind=='gnarly') else 1
    tt=int(H*0.45)
    trunk(x,z,y,y+tt+1,log,th_)
    xs,zs,ys=crown(x,z,y,tt,H*0.9,W,log,LV,int(rng.integers(4,7)),0.75,1)
    roots(x,z,y,log,th_,int(rng.integers(3,5)),max(2,int(1.5*F)))
    buttons(x,z,y+1,y+tt,log,th_,2)
    trunk_vines(x,z,y,y+tt,th_,0.3)
    hang(*bottoms(xs,zs,ys),0.14,'moss',int(5*F))
    petals(x,z,int(W*0.5),int(W*W*0.25),'leaf_litter')
    for _ in range(int(W)):  # pale moss carpet patches
        a=x+int(rng.integers(-int(W*0.5),int(W*0.5)+1)); b=z+int(rng.integers(-int(W*0.5),int(W*0.5)+1))
        if 0<=a<NX and 0<=b<NZ and air(a,b,gt[a,b]+1): B[a,b,gt[a,b]+1]=P('pale_moss_carpet',bottom='true',east='none',north='none',south='none',west='none')
def t_bamboo(x,z,y,h,w):
    n=max(5,int(w*S*1.2)); r=max(1.5,w*S*0.42)
    for _ in range(n):
        a=x+int(round(rng.uniform(-r,r))); b=z+int(round(rng.uniform(-r,r)))
        if not(0<=a<NX and 0<=b<NZ) or water[a,b]: continue
        y0=gt[a,b]+1; hh=int(max(5,h*S*rng.uniform(0.6,1.05))); age=int(rng.random()<0.6)
        for j in range(hh):
            if not air(a,b,y0+j): break
            lv='large' if j>=hh-2 else ('small' if j==hh-3 else 'none')
            B[a,b,y0+j]=P('bamboo',age=age,leaves=lv,stage=0)
def t_bush(x,z,y,h,w,sp):
    kind=None; LV=SPEC[sp][1]
    rx=max(1.6,w*S*0.3); ry=max(1.1,h*S*0.75)
    blob(x+rng.uniform(-0.5,0.5),z+rng.uniform(-0.5,0.5),y+ry*0.25,rx,ry,*LV,rough=0.45,rz=rx*rng.uniform(0.7,1.2))
    if rng.random()<0.5: blob(x+rng.uniform(-rx,rx)*0.6,z+rng.uniform(-rx,rx)*0.6,y,rx*0.6,ry*0.8,*LV,rough=0.45)
TR=json.load(open(D+'trees.json')); order=rng.permutation(len(TR)); cnt={}
for i in order:
    t=TR[i]; x=int((YMAX-t['y'])*S); z=int((XMAX-t['x'])*S)
    if not(2<=x<NX-3 and 2<=z<NZ-3) or not inside[x,z] or water[x,z]: continue
    if SPECIAL_ZONE[x,z]: continue
    y=int(gt[x,z])+1; dire=bool(DIRE[x,z]); k=t['t']
    sp=species(k,t['leaf'],dire)
    if k=='pine': t_pine(x,z,y,t['h'],t['w'],dire)
    elif k=='oak': t_oak(x,z,y,t['h'],t['w'],sp,dire)
    elif k=='dire_small': (t_dire_small if dire else t_oak)(x,z,y,t['h'],t['w'],sp,*(() if dire else (dire,)))
    elif k in ('dire_big','gnarly'): (t_big(x,z,y,t['h'],t['w'],k,sp) if dire else t_oak(x,z,y,t['h'],t['w'],sp,dire))
    elif k=='bamboo': t_bamboo(x,z,y,t['h'],t['w'])
    elif k in ('bush_r','bush_d'): t_bush(x,z,y,t['h'],t['w'],sp)
    cnt[k+':'+sp]=cnt.get(k+':'+sp,0)+1
print('trees',cnt,time.time()-T,flush=True)
# leftover tree voxels (ancient tree, portal tree, roots): logs + azalea leaves
ws=np.nonzero(np.asarray(CAT)==7); ls=np.nonzero(np.asarray(CAT)==6)
m=B[ws]==0; dd=DIRE[ws[0],ws[1]]
B[ws[0][m],ws[1][m],ws[2][m]]=np.where(dd[m],P('dark_oak_log',axis='y'),P('birch_log',axis='y'))
m=B[ls]==0; dd=DIRE[ls[0],ls[1]]
B[ls[0][m],ls[1][m],ls[2][m]]=np.where(dd[m],LPi('dark_oak_leaves'),LPi('birch_leaves'))
# ---------- vines -------------
vs=np.nonzero(np.asarray(CAT)==3); nv=0
for x,z,y in zip(*vs):
    if B[x,z,y]: continue
    pr={'east':B[min(x+1,NX-1),z,y]>0,'west':B[max(x-1,0),z,y]>0,'south':B[x,min(z+1,NZ-1),y]>0,'north':B[x,max(z-1,0),y]>0,'up':B[x,z,min(y+1,NY-1)]>0}
    if any(pr.values()): B[x,z,y]=P('vine',**{k:str(bool(v)).lower() for k,v in pr.items()}); nv+=1
print('vines',nv,time.time()-T,flush=True)
# ---------- ground vegetation -------------
canopy=ndi.maximum_filter(CAN.astype(np.uint8),int(3*F)+2)>0
Lp=np.load(OD+'L_plant.npz'); Hp,Cp,Mp=Lp['H'],Lp['C'],Lp['M']
pname=np.array(MN+[''],object)[np.where(Mp>=0,Mp,len(MN))]
topid=B[np.arange(NX)[:,None],np.arange(NZ)[None,:],np.clip(gt,0,NY-1)]
topn=np.array([s.split('[')[0].split(':')[1] for s in pal],object)[topid]
gx,gz=np.nonzero(inside&~water)
ok=np.array([air(x,z,gt[x,z]+1) for x,z in zip(gx,gz)])
gx,gz=gx[ok],gz[ok]
FLW=['poppy','dandelion','cornflower','oxeye_daisy','azure_bluet','allium','blue_orchid','red_tulip','orange_tulip','pink_tulip','white_tulip','lily_of_the_valley','torchflower']
nearwater=ndi.binary_dilation(water,iterations=int(6*F))
stats={}
_g=ndi.gaussian_filter(rng.random((NX,NZ)).astype(np.float32),3*F); PATCH=(_g-_g.mean())/_g.std()
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
            if PATCH[x,z]>0.8 and r<0.9: put(x,z,y,'pale_moss_carpet',bottom='true',east='none',north='none',south='none',west='none')
            elif r<0.12: put(x,z,y,'leaf_litter',facing=HORZ[int(rng.integers(4))],segment_amount=int(rng.integers(1,5)))
            elif r<0.43: put(x,z,y,'brown_mushroom')
            elif r<0.45: put(x,z,y,'dead_bush')
        else:
            if r<0.10: put(x,z,y,'short_dry_grass')
            elif r<0.14: put(x,z,y,'tall_dry_grass')
            elif r<0.16: put(x,z,y,'dead_bush')
            elif r<0.165: put(x,z,y,'brown_mushroom')
    else:
        if canopy[x,z]:
            if PATCH[x,z]>0.9 and r<0.9: put(x,z,y,'moss_carpet')
            elif r<0.12: put(x,z,y,'leaf_litter',facing=HORZ[int(rng.integers(4))],segment_amount=int(rng.integers(1,5)))
            elif r<0.33: put(x,z,y,'fern')
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
np.save(OD+'B_final.npy',B); json.dump(pal,open(OD+'pal_final.json','w'))
print('DONE',len(pal),(B>0).sum(),time.time()-T)

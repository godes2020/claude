# Hand-designed landmarks: lotus pools, shrines of wisdom, twin gates.
import numpy as np, json, os, time
T=time.time(); OD=os.environ['OD']
B=np.load(OD+'B_final.npy'); pal=json.load(open(OD+'pal_final.json')); pid={s:i for i,s in enumerate(pal)}
SG=np.load(OD+'stage_ground.npz'); gt,DIRE=SG['gt'],SG['DIRE']
SPJ=json.load(open(OD+'special.json'))
NX,NZ,NY=B.shape
def P(name,**pr):
    s='minecraft:'+name+('['+','.join(f'{k}={str(v).lower()}' for k,v in sorted(pr.items()))+']' if pr else '')
    if s not in pid: pid[s]=len(pal); pal.append(s)
    return pid[s]
def put(x,z,y,name,**pr):
    if 0<=x<NX and 0<=z<NZ and 0<=y<NY: B[x,z,y]=0 if name=='air' else P(name,**pr)
CCW={'north':'west','west':'south','south':'east','east':'north'}
OPP={'north':'south','south':'north','east':'west','west':'east'}
DV={'east':(1,0),'west':(-1,0),'south':(0,1),'north':(0,-1)}
def toward(dx,dz):
    """horizontal direction pointing along (dx,dz)"""
    if abs(dx)>=abs(dz): return 'east' if dx>0 else 'west'
    return 'south' if dz>0 else 'north'
def stairs_ring(cells,mat):
    """cells: dict (x,z,y)->facing. Places bottom stairs with vanilla shape rules."""
    def st(p): return cells.get(p)
    for (x,z,y),f in cells.items():
        shape='straight'
        dx,dz=DV[f]; n1=st((x+dx,z+dz,y))
        if n1 and DV[n1][0]*dx+DV[n1][1]*dz==0:
            ox,oz=DV[OPP[n1]]; c=st((x+ox,z+oz,y))
            if c!=f: shape='outer_left' if n1==CCW[f] else 'outer_right'
        if shape=='straight':
            n2=st((x-dx,z-dz,y))
            if n2 and DV[n2][0]*dx+DV[n2][1]*dz==0:
                ox,oz=DV[n2]; c=st((x+ox,z+oz,y))
                if c!=f: shape='inner_left' if n2==CCW[f] else 'inner_right'
        put(x,z,y,mat,facing=f,half='bottom',shape=shape,waterlogged='false')
def level(cx,cz,r):
    ii,jj=np.mgrid[int(cx-r):int(cx+r)+1,int(cz-r):int(cz+r)+1]
    m=(ii-cx)**2+(jj-cz)**2<=r*r
    return int(np.round(np.median(gt[ii[m],jj[m]])))
def prepare(cx,cz,r,g,floor):
    """clear everything above g inside radius r, make solid columns up to g"""
    for x in range(int(cx-r)-1,int(cx+r)+2):
        for z in range(int(cz-r)-1,int(cz+r)+2):
            if not(0<=x<NX and 0<=z<NZ) or (x-cx)**2+(z-cz)**2>r*r: continue
            B[x,z,g+1:]=0
            lo=min(gt[x,z],g)-2
            for y in range(max(lo,0),g): B[x,z,y]=P('stone') if y<g-1 else P('dirt' if floor!='stone' else 'stone')
            B[x,z,g]=P(floor)
# ======================= LOTUS POOL =======================
def lotus(cx,cz):
    g=level(cx,cz,20); R=22
    prepare(cx,cz,R+2,g,'grass_block')
    GAPS=np.deg2rad([30,150,270])
    pads=[(cx+13*np.cos(a),cz+13*np.sin(a)) for a in np.deg2rad([0,60,120,180,240,300])]
    x0,z0=int(cx-R)-1,int(cz-R)-1; n=2*R+4
    gx,gz=np.mgrid[x0:x0+n,z0:z0+n]; dx,dz=gx+0.5-cx,gz+0.5-cz; r=np.hypot(dx,dz)
    ingap=np.zeros(r.shape,bool)
    for a in GAPS: ingap|=(np.abs(-np.sin(a)*dx+np.cos(a)*dz)<=2.6)&((np.cos(a)*dx+np.sin(a)*dz)>0)
    basin=(r>=10.5)&(r<=15.5)&~ingap
    from scipy import ndimage as ndi
    wall=ndi.binary_dilation(basin,np.ones((3,3),bool))&~basin
    ang=(np.degrees(np.arctan2(dz,dx))+360)%360
    for (x,z),rr in np.ndenumerate(r):
        X,Z=gx[x,z],gz[x,z]
        if rr>R: continue
        if wall[x,z]:
            pil=min(ang[x,z]%20,20-ang[x,z]%20)<1.6
            put(X,Z,g,'stone_bricks'); put(X,Z,g+1,'chiseled_stone_bricks' if pil else 'stone_bricks'); put(X,Z,g+2,'polished_andesite')
        elif basin[x,z]:
            put(X,Z,g-1,'stone'); put(X,Z,g,'mud'); put(X,Z,g+1,'water',level=0)
        elif rr>R-1.5: put(X,Z,g,'mossy_stone_bricks')
        elif rr>R-2.5: put(X,Z,g,'polished_andesite')
        else: put(X,Z,g,'stone_bricks')
    for px,pz in pads:
        px,pz=int(round(px-0.5)),int(round(pz-0.5))
        put(px,pz,g+1,'moss_block'); put(px,pz,g+2,'pink_petals',facing='north',flower_amount=4)
        for a,b in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
            if pal[B[px+a,pz+b,g+1]]=='minecraft:water[level=0]' and (a*b==0 or (px+pz+a)%2==0): put(px+a,pz+b,g+2,'lily_pad')
    # centre: two-step dais with correct stairs, column and glowing lotus bud
    c0x,c0z=int(np.floor(cx)),int(np.floor(cz))
    st={}
    for x in range(c0x-6,c0x+7):
        for z in range(c0z-6,c0z+7):
            dx,dz=x+0.5-cx,z+0.5-cz; r=np.hypot(dx,dz)
            if r<=4.6: put(x,z,g+1,'chiseled_stone_bricks' if r<=1.6 else 'polished_andesite')
            elif r<=5.6: st[(x,z,g+1)]=toward(-dx,-dz)
            if r<=2.6: put(x,z,g+2,'stone_bricks')
            elif r<=3.6: st[(x,z,g+2)]=toward(-dx,-dz)
    stairs_ring(st,'stone_brick_stairs')
    for y in range(g+3,g+6):
        for a in (-1,0,1):
            for b in (-1,0,1):
                if a==0 or b==0 or y==g+3: put(c0x+a,c0z+b,y,'chiseled_stone_bricks' if a==b==0 else 'stone_bricks')
    prof=[1.2,1.9,2.3,2.3,1.9,1.3,0.7]
    for k,rr in enumerate(prof):
        y=g+6+k
        for a in range(-3,4):
            for b in range(-3,4):
                d=np.hypot(a,b)
                if d<=rr: put(c0x+a,c0z+b,y,'pearlescent_froglight' if d<=rr-1.0 else 'pink_stained_glass')
    put(c0x,c0z,g+6+len(prof),'pink_stained_glass')
    # four green leaf petals below the bud
    for a,b in ((1,0),(-1,0),(0,1),(0,-1)):
        put(c0x+2*a,c0z+2*b,g+5,'moss_block'); put(c0x+3*a,c0z+3*b,g+5,'moss_block')
    return g
# ======================= SHRINE OF WISDOM =======================
def shrine(cx,cz):
    g=level(cx,cz,10); R=10.6
    prepare(cx,cz,R+3,g,'grass_block')
    st1={}; st2={}
    for x in range(int(cx-R)-2,int(cx+R)+3):
        for z in range(int(cz-R)-2,int(cz+R)+3):
            dx,dz=x+0.5-cx,z+0.5-cz; r=np.hypot(dx,dz)
            if r>R+1: continue
            if r>R: st1[(x,z,g+1)]=toward(-dx,-dz); continue
            # level 1 platform
            ang=(np.degrees(np.arctan2(dz,dx))+360)%45
            if r>R-1.2: m='purpur_pillar'
            elif 6.5<r<=7.5: m='purple_stained_glass'
            elif r<=6.5 and (abs(dx)<=0.6 or abs(dz)<=0.6): m='purple_stained_glass'
            else: m='purpur_block'
            if m=='purple_stained_glass': put(x,z,g,'amethyst_block')
            if m=='purpur_pillar': put(x,z,g+1,'purpur_pillar',axis='y')
            else: put(x,z,g+1,m)
            # level 2 dais
            if r<=3.6: put(x,z,g+2,'amethyst_block' if r<=1.6 else 'purpur_block')
            elif r<=4.6: st2[(x,z,g+2)]=toward(-dx,-dz)
    stairs_ring(st1,'purpur_stairs'); stairs_ring(st2,'purpur_stairs')
    c0x,c0z=int(np.floor(cx)),int(np.floor(cz))
    # floating crystal: diamond of purple glass over an amethyst core
    base=g+6
    for k in range(9):
        rr=[0.5,1.2,1.8,2.2,2.2,1.8,1.3,0.8,0.4][k]
        for a in range(-3,4):
            for b in range(-3,4):
                d=np.hypot(a,b)
                if d<=rr: put(c0x+a,c0z+b,base+k,'amethyst_block' if d<=rr-1.0 else 'purple_stained_glass')
    put(c0x,c0z,base-1,'amethyst_cluster',facing='down',waterlogged='false')
    put(c0x,c0z,base+9,'amethyst_cluster',facing='up',waterlogged='false')
    # orbiting floating stones
    for i,a in enumerate(np.deg2rad(np.arange(0,360,60)+15)):
        sx,sz=int(round(cx+6.5*np.cos(a)-0.5)),int(round(cz+6.5*np.sin(a)-0.5)); sy=g+5+(i%3)
        put(sx,sz,sy,'purpur_block'); put(sx,sz,sy-1,'crying_obsidian')
        put(sx,sz,sy+1,'amethyst_cluster',facing='up',waterlogged='false')
    return g
# ======================= TWIN GATE =======================
def portal(cx,cz):
    g=level(cx,cz,9); dire=bool(DIRE[int(cx),int(cz)])
    M=dict(ring='polished_blackstone_bricks',acc='gilded_blackstone',inner='crying_obsidian',glass='purple_stained_glass',floor='polished_blackstone',edge='blackstone',stair='polished_blackstone_brick_stairs',light='shroomlight') if dire else \
      dict(ring='stone_bricks',acc='chiseled_stone_bricks',inner='prismarine_bricks',glass='light_blue_stained_glass',floor='polished_andesite',edge='mossy_stone_bricks',stair='stone_brick_stairs',light='sea_lantern')
    RX,RZ=12.5,9.5
    prepare(cx,cz,RX+3,g,'grass_block')
    st={}
    for x in range(int(cx-RX)-2,int(cx+RX)+3):
        for z in range(int(cz-RZ)-2,int(cz+RZ)+3):
            dx,dz=x+0.5-cx,z+0.5-cz; e=(dx/RX)**2+(dz/RZ)**2
            e1=(dx/(RX+1))**2+(dz/(RZ+1))**2
            if e<=1:
                put(x,z,g+1,M['edge'] if e>0.8 else (M['acc'] if abs(dz)<=0.6 and abs(dx)>3 else M['floor']))
            elif e1<=1: st[(x,z,g+1)]=toward(-dx/RX**2,-dz/RZ**2)
    stairs_ring(st,M['stair'])
    # vertical ring in the X-Y plane, 3 blocks thick in Z
    Ro,Ri=10.5,7.2; cy=g+2+Ro; z0=int(np.floor(cz))
    for x in range(int(cx-Ro)-1,int(cx+Ro)+2):
        for y in range(g+2,int(cy+Ro)+2):
            d=np.hypot(x+0.5-cx,y+0.5-cy)
            ang=(np.degrees(np.arctan2(y+0.5-cy,x+0.5-cx))+360)%360
            for dz in (-1,0,1):
                if Ri<=d<=Ro:
                    if d>=Ro-1.0 or abs(dz)==1 and d>=Ro-2: m=M['ring']
                    elif d<Ri+1.0: m=M['inner']
                    else: m=M['ring']
                    if dz==0 and d>=Ri+1 and d<Ro-1 and min(ang%45,45-ang%45)<4: m=M['acc']
                    put(x,z0+dz,y,m)
                elif d<Ri and dz==0: put(x,z0,y,M['glass'])
    # keystone and side lights
    put(int(cx),z0,int(cy+Ro)-1,M['light']); put(int(cx),z0-1,int(cy+Ro)-1,M['acc']); put(int(cx),z0+1,int(cy+Ro)-1,M['acc'])
    for sx in (-1,1):
        put(int(cx+sx*(Ro-0.5)),z0-1,int(cy),M['light']); put(int(cx+sx*(Ro-0.5)),z0+1,int(cy),M['light'])
    if not dire:  # moss and leaves draping over the Radiant gate
        for x in range(int(cx-Ro),int(cx+Ro)+1):
            for dz in (-1,0,1):
                for y in range(int(cy+Ro)+1,int(cy)-1,-1):
                    if B[x,z0+dz,y]!=0:
                        if np.hypot(x+0.5-cx,y+0.5-cy)>Ri+1 and (x*7+dz*3)%5<2: put(x,z0+dz,y+1,'moss_block')
                        break
    return g

# ======================= BARRACKS =======================
def MAT(dire):
    if dire: return dict(wall='polished_blackstone_bricks',pil=('polished_basalt',True),band='red_nether_bricks',corn='polished_blackstone',door='crying_obsidian',
        plinth='blackstone',pst='blackstone_stairs',roof='red_nether_bricks',rst='red_nether_brick_stairs',fin='gilded_blackstone',light='shroomlight',floor='coarse_dirt')
    return dict(wall='stone_bricks',pil=('quartz_pillar',True),band='chiseled_stone_bricks',corn='smooth_stone',door='dark_oak_planks',
        plinth='polished_andesite',pst='stone_brick_stairs',roof='oxidized_cut_copper',rst='oxidized_cut_copper_stairs',fin='gold_block',light='sea_lantern',floor='grass_block')
def pil(M,x,z,y):
    n,ax=M['pil']; put(x,z,y,n,axis='y') if ax else put(x,z,y,n)
def melee(cx,cz):
    dire=bool(DIRE[int(cx),int(cz)]); M=MAT(dire); g=level(cx,cz,9)
    prepare(cx,cz,12.5,g,M['floor']); X,Z=int(cx),int(cz)
    st={}
    for a in range(-8,9):
        for b in range(-8,9):
            m=max(abs(a),abs(b))
            if m<=7: put(X+a,Z+b,g+1,M['plinth'])
            else: st[(X+a,Z+b,g+1)]=toward(-a,-b)
    stairs_ring(st,M['pst'])
    H=6  # walls g+2..g+7
    for a in range(-5,6):
        for b in range(-5,6):
            for y in range(g+2,g+2+H):
                put(X+a,Z+b,y,M['band'] if y==g+5 and max(abs(a),abs(b))==5 else M['wall'])
    # corner pillars (2x2, protruding) with lights
    for sa in (-1,1):
        for sb in (-1,1):
            for a in (5*sa,6*sa):
                for b in (5*sb,6*sb):
                    for y in range(g+2,g+2+H+2): pil(M,X+a,Z+b,y)
            put(X+6*sa,Z+6*sb,g+2+H+2,M['light'])
    # recessed arched doorways on every face
    for d,(dx,dz) in DV.items():
        px,pz=-dz,dx
        for w in (-1,0,1):
            for y in range(g+2,g+6 if w==0 else g+5):
                put(X+5*dx+w*px,Z+5*dz+w*pz,y,'air'); put(X+4*dx+w*px,Z+4*dz+w*pz,y,M['door'])
        put(X+5*dx,Z+5*dz,g+6,M['band'])
        # pilasters beside the door
        for w in (-3,3):
            for y in range(g+2,g+2+H): pil(M,X+6*dx+w*px,Z+6*dz+w*pz,y)
    # cornice overhang
    for a in range(-6,7):
        for b in range(-6,7):
            if max(abs(a),abs(b))>=5: put(X+a,Z+b,g+2+H,M['corn'])
    # stepped roof with stairs on each step
    for k,hw in enumerate([5,4,3,2,1]):
        y=g+3+H+k; st={}
        for a in range(-hw,hw+1):
            for b in range(-hw,hw+1):
                if max(abs(a),abs(b))==hw: st[(X+a,Z+b,y)]=toward(-a,-b)
                else: put(X+a,Z+b,y,M['roof'])
        stairs_ring(st,M['rst'])
    yt=g+3+H+5
    put(X,Z,yt,M['roof']); put(X,Z,yt+1,M['fin']); put(X,Z,yt+2,M['light'])
    return g
def ranged(cx,cz):
    dire=bool(DIRE[int(cx),int(cz)]); M=MAT(dire); g=level(cx,cz,8)
    prepare(cx,cz,11.5,g,M['floor']); X,Z=int(cx),int(cz)
    st={}
    for a in range(-10,11):
        for b in range(-10,11):
            r=np.hypot(a,b)
            if r<=8.2: put(X+a,Z+b,g+1,M['plinth'])
            elif r<=9.2: st[(X+a,Z+b,g+1)]=toward(-a,-b)
    stairs_ring(st,M['pst'])
    top=g+12
    for a in range(-7,8):
        for b in range(-7,8):
            r=np.hypot(a,b); ang=(np.degrees(np.arctan2(b,a))+360)%45
            for y in range(g+2,top):
                if r<=5.2: put(X+a,Z+b,y,M['band'] if y in (g+6,g+10) and r>4.2 else M['wall'])
                elif r<=6.4 and min(ang,45-ang)<7 and y<top-1: pil(M,X+a,Z+b,y)
            if r<=6.4: put(X+a,Z+b,top,M['corn'])
            if 5.4<r<=6.4 and ((a+b)%2==0): put(X+a,Z+b,top+1,M['wall'])
    # glowing windows and a doorway
    for d,(dx,dz) in DV.items():
        for y in (g+8,g+9): put(X+5*dx,Z+5*dz,y,M['light'])
    dx,dz=DV['south'] if not dire else DV['north']
    for w in (-1,0,1):
        for y in range(g+2,g+5 if w else g+6):
            put(X+5*dx-w*dz,Z+5*dz+w*dx,y,'air'); put(X+4*dx-w*dz,Z+4*dz+w*dx,y,M['door'])
    # conical roof with stairs rings
    for k,rr in enumerate([4.6,3.8,3.0,2.3,1.6,1.0]):
        y=top+1+k; st={}
        for a in range(-5,6):
            for b in range(-5,6):
                r=np.hypot(a,b)
                if r<=rr-1: put(X+a,Z+b,y,M['roof'])
                elif r<=rr: st[(X+a,Z+b,y)]=toward(-a,-b)
        stairs_ring(st,M['rst'])
    y=top+7
    put(X,Z,y,M['roof']); put(X,Z,y+1,M['fin']); put(X,Z,y+2,M['fin']); put(X,Z,y+3,M['light'])
    return g
for c in SPJ['lotus']: print('lotus',c,lotus(*c))
for c in SPJ['shrine']: print('shrine',c,shrine(*c))
np.save(OD+'B_final.npy',B); json.dump(pal,open(OD+'pal_final.json','w'))
print('DONE',len(pal),time.time()-T)

import numpy as np, json, time
T=time.time(); D='/home/user/dota_work/mc/'
G=json.load(open(D+'grid.json')); NX,NY,NZ=G['NX'],G['NY'],G['NZ']
r=np.load(D+'raw_vox.npz'); idx,ci,rgb,m=r['a'],r['b'],r['c'],r['m']
key=idx*16+ci
o=np.argsort(key,kind='stable'); key=key[o]; rgb=rgb[o].astype(np.float32); m=m[o]
u,st,cnt=np.unique(key,return_index=True,return_counts=True)
csum=np.add.reduceat(rgb,st,axis=0); cm=(csum/cnt[:,None]).astype(np.uint8)
mm=m[st]
vidx=u//16; vc=(u%16).astype(np.uint8)
# keep max category per voxel (last in sorted order per vidx)
last=np.r_[vidx[1:]!=vidx[:-1],True]
vidx,vc,cm,mm,cnt=vidx[last],vc[last],cm[last],mm[last],cnt[last]
print('VOXELS',len(vidx),np.bincount(vc),time.time()-T)
CAT=np.zeros(NX*NY*NZ,np.uint8); CAT[vidx]=vc
COL=np.zeros((NX*NY*NZ,3),np.uint8); COL[vidx]=cm
MAT=np.full(NX*NY*NZ,-1,np.int16); MAT[vidx]=mm
np.save(D+'CAT.npy',CAT.reshape(NX,NZ,NY)); np.save(D+'COL.npy',COL.reshape(NX,NZ,NY,3)); np.save(D+'MAT.npy',MAT.reshape(NX,NZ,NY))
# 2D layers: top sample per column
for k in ('decal','plant','water'):
    r=np.load(D+f'raw_{k}.npz'); col,z,c,mt=r['a'],r['b'],r['c'],r['m']
    o=np.lexsort((z,col)); col,z,c,mt=col[o],z[o],c[o],mt[o]
    last=np.r_[col[1:]!=col[:-1],True]
    H=np.full(NX*NZ,-1.0,np.float32); H[col[last]]=z[last]
    C=np.zeros((NX*NZ,3),np.uint8); C[col[last]]=c[last]
    Mt=np.full(NX*NZ,-1,np.int16); Mt[col[last]]=mt[last]
    np.savez(D+f'L_{k}.npz',H=H.reshape(NX,NZ),C=C.reshape(NX,NZ,3),M=Mt.reshape(NX,NZ))
    print(k,last.sum())
print('DONE',time.time()-T)

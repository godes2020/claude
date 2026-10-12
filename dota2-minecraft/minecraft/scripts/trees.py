# Extract tree instances (world coords) from exported triangles
import json, numpy as np, collections
D='/home/user/dota_work/mc/'
m=json.load(open(D+'meta.json')); o=np.load(D+'obj.npy'); mat=np.load(D+'mat.npy'); X=np.load(D+'xyz.npy',mmap_mode='r')
MN=[x['name'].lower() for x in m['mats']]; objs=m['objs']
TYPES=[('n0_lr0_agg_prop_tree_oak_leaves_05','bush_r'),('n0_lr0_agg_prop_tree_oak_leaves_08','bush_d'),('n0_lr0_agg_prop_tree_oak_leaves_blank','skip'),
 ('n0_lr0_agg_prop_tree_gnarly','gnarly'),('tree_pine','pine'),('dire_tree004','dire_small'),('dire_tree007','dire_big'),('dire_tree008','dire_big'),
 ('tree_oak','oak'),('tree_cine','oak'),('tree_bamboo','bamboo')]
def typ(n):
    for p,t in TYPES:
        if n.startswith(p): return t
    return None
otype=[typ(n) for n in objs]
isinst=np.array([t is not None for t in otype])
np.save(D+'tree_obj_mask.npy',isinst)
sel=np.nonzero(isinst[o])[0]; oo=o[sel]; P=np.asarray(X[sel])
mn=np.full((len(objs),3),1e9); mx=np.full((len(objs),3),-1e9)
np.minimum.at(mn,oo,P.min(1)); np.maximum.at(mx,oo,P.max(1))
mc=collections.defaultdict(collections.Counter)
for t,ob in zip(mat[sel],oo): mc[ob][MN[t]]+=1
out=[]
for i in np.unique(oo):
    t=otype[i]
    if t=='skip': continue
    leaf='green'
    names=' '.join(mc[i])
    if 'redblossom' in names: leaf='red'
    elif 'blossoms_white' in names: leaf='white'
    elif 'magical_white' in names: leaf='magic_white'
    elif 'magical_pink' in names or 'plumblossom' in names: leaf='pink'
    c=(mn[i]+mx[i])/2
    out.append(dict(t=t,leaf=leaf,x=float(c[0]),y=float(c[1]),z0=float(mn[i][2]),h=float(mx[i][2]-mn[i][2]),w=float(max(mx[i][0]-mn[i][0],mx[i][1]-mn[i][1]))))
json.dump(out,open(D+'trees.json','w'))
print(len(out),collections.Counter((d['t'],d['leaf']) for d in out))

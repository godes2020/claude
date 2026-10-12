import bpy, numpy as np, json, time, re
T=time.time()
bad=('black','petals_plumblossom','leaves_white000','dota_nav_walkable','solid_white','glow_00','vapor','lightrays','cracks_glow','liquid_pour','dark_statue_fade','web_fall')
skipobj=('n_creep','shopkeeper','camera','wildlife')
def img_of(sock,depth=0):
    for l in sock.links:
        n=l.from_node
        if n.type=='TEX_IMAGE': return n.image, l.from_socket.name
        if depth<4:
            for i in n.inputs:
                r=img_of(i,depth+1)
                if r: return r
    return None
mats={}
def matinfo(m):
    if m is None: return None
    if m.name in mats: return m.name
    d={'name':m.name}
    if m.use_nodes:
        p=next((x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED'),None)
        if p:
            r=img_of(p.inputs['Base Color'])
            if r: d['img']=bpy.path.abspath(r[0].filepath)
            else: d['col']=list(p.inputs['Base Color'].default_value)[:3]
            a=img_of(p.inputs['Alpha'])
            if a: d['aimg']=bpy.path.abspath(a[0].filepath); d['asock']=a[1]
    mats[m.name]=d; return m.name
XYZ=[];UV=[];MAT=[];OBJ=[];onames=[];mnames=[];mid={}
dg=bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type!='MESH' or any(k in o.name.lower() for k in skipobj): continue
    me=o.data
    if not me.polygons: continue
    ms=[s.material for s in o.material_slots]
    okm=[ (m is not None) and not any(b in m.name.lower() for b in bad) for m in ms] or [True]
    if not any(okm): continue
    me.calc_loop_triangles()
    nt=len(me.loop_triangles)
    if nt==0: continue
    v=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',v); v=v.reshape(-1,3)
    M=np.array(o.matrix_world,dtype=np.float64); v=(v@M[:3,:3].T+M[:3,3]).astype(np.float32)
    tv=np.empty(nt*3,np.int32); me.loop_triangles.foreach_get('vertices',tv); tv=tv.reshape(-1,3)
    tl=np.empty(nt*3,np.int32); me.loop_triangles.foreach_get('loops',tl); tl=tl.reshape(-1,3)
    tm=np.empty(nt,np.int32); me.loop_triangles.foreach_get('material_index',tm)
    if me.uv_layers:
        uvl=me.uv_layers.active or me.uv_layers[0]
        uv=np.empty(len(me.loops)*2,np.float32); uvl.data.foreach_get('uv',uv); uv=uv.reshape(-1,2)
        tuv=uv[tl]
    else: tuv=np.zeros((nt,3,2),np.float32)
    gm=np.full(len(ms) or 1,-1,np.int32)
    for i,m in enumerate(ms):
        if okm[i] and m is not None:
            nm=matinfo(m)
            if nm not in mid: mid[nm]=len(mnames); mnames.append(nm)
            gm[i]=mid[nm]
    tm=gm[np.clip(tm,0,len(gm)-1)]
    keep=tm>=0
    XYZ.append(v[tv][keep]); UV.append(tuv[keep]); MAT.append(tm[keep].astype(np.int16)); OBJ.append(np.full(keep.sum(),len(onames),np.int32)); onames.append(o.name)
XYZ=np.concatenate(XYZ); UV=np.concatenate(UV); MAT=np.concatenate(MAT); OBJ=np.concatenate(OBJ)
print('TRIS',len(XYZ),'OBJS',len(onames),'MATS',len(mnames),time.time()-T)
np.save('/home/user/dota_work/mc/xyz.npy',XYZ); np.save('/home/user/dota_work/mc/uv.npy',UV); np.save('/home/user/dota_work/mc/mat.npy',MAT); np.save('/home/user/dota_work/mc/obj.npy',OBJ)
json.dump({'objs':onames,'mats':[mats[n] for n in mnames]},open('/home/user/dota_work/mc/meta.json','w'))
print('SAVED',time.time()-T)

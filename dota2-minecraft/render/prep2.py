import bpy, time
T=time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='/home/user/dota_work/tex/x/dota_d.gltf')
print('IMPORT',time.time()-T)
drop=('inspector','physics','destruction','dest_','_sfm','stump','vapors','lightrays','toolsclip','tools_','nodraw','skybox_','clip')
n=0
for o in list(bpy.data.objects):
    nm=(o.name+' '+(o.data.name if o.data else '')).lower()
    mats=' '.join(m.name.lower() for m in (o.data.materials if o.type=='MESH' else []) if m)
    if o.type=='MESH' and (any(k in nm for k in drop) or any(k in mats for k in ('tools','nodraw','toolsblock','clip','trigger','black_unlit','dev/'))):
        bpy.data.objects.remove(o, do_unlink=True); n+=1
print('DROPPED',n)
import collections
c=collections.Counter(m.name for m in bpy.data.materials if m.users)
print('MATS',len(c)); print(sorted(c)[:400])
bpy.ops.wm.save_as_mainfile(filepath='/home/user/dota_work/render/scene_tex.blend')
print('SAVED',time.time()-T)

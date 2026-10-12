import bpy
bpy.ops.import_scene.gltf(filepath='/home/user/dota_work/tex/x/destr.gltf')
print('ADDED',[o.name for o in bpy.context.selected_objects])
bpy.ops.wm.save_mainfile()
print('SAVED')

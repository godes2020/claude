# Dota 2 map in Minecraft 1.21.11

`dota2_map.litematic` is a Litematica schematic for Minecraft 1.21.11 (DataVersion 4667).

- Size: 956 × 111 × 1004 blocks (X × Y × Z), 1.85 blocks per metre of the original map (about 1k × 1k).
- About 5.26 million blocks, 142 block types, 430 block states. Every state was checked against the 1.21.11 block list.
- Orientation: the Radiant base is at small X / large Z (south-west), and the Dire base is at large X / small Z (north-east).

## What's in it

- Terrain is made of solid full blocks laid out in large, even patches (smoothed colour plus a majority filter), with no single-block speckle:
  - Radiant: grass, podzol and moss, with stone, andesite and cobblestone patches.
  - Dire: coarse dirt, packed mud, rooted dirt, gravel and soul soil.
  - Lanes and paths: coarse dirt, packed mud, gravel, stone bricks.
  - There is no lava. Lava areas are magma_block.
- Cliffs and slopes use smooth low-frequency patches:
  - Radiant: stone, andesite, tuff and cobblestone, with mossy cobblestone under the grass.
  - Dire: tuff, deepslate, cobbled deepslate and blackstone.
- River:
  - water whose depth grows towards the middle;
  - bed of mud, clay, gravel and sand;
  - seagrass, sea pickles and lily pads.
- Trees are generated procedurally from 4,715 Dota tree positions, each with its own height and crown size:
  - pines are layered spruces with drooping branch tips;
  - oaks have thick trunks, branches, several crown clumps, roots with buttons, vines and cave vines;
  - blossom trees use cherry, pale oak and flowering azalea leaves;
  - Dire trees are crooked dark oak and pale oak with twig fences, hanging moss and mangrove roots at the base;
  - there are also bamboo and bushes.
- Buildings (towers, barracks, fountains, shops, camps):
  - full blocks only, so roofs, overhangs and floors have no gaps;
  - each building material uses 1–3 blocks, smoothed between neighbours;
  - no stairs, wall or fence posts, shelves or hanging lanterns;
  - decorations are kept on top: candles, torches, the lanterns of sight, pots, barrels and the Dire chains.
- Grass:
  - grass, ferns, flowers and wildflowers;
  - moss carpet patches under the trees;
  - dry grass in the Dire.

## How to use it

Put the file in `.minecraft/schematics/` (Litematica + MaLiLib for 1.21.11). Paste it on a flat world with `/litematica` or with the Easy Place / Paste mode. The schematic is large, so on a server raise the paste limits or paste in parts.

## Scripts (`scripts/`)

1. `export_tris.py` (Blender): exports the map's triangles from the glTF.
2. `trees.py`: finds the tree instances (type, position, height, crown) and masks them out of the voxelization.
3. `voxelize.py`, `aggregate.py`: voxelize the triangles and sample texture colours (`S=1.85 OD=<dir>`).
4. `palette.py`: computes average colours from the real 1.21.11 textures.
5. `build.py`: terrain, cliffs, water and buildings.
6. `build2.py`: procedural trees, vegetation and connections.
7. `write_lit.py`, `write_schem.py`: write the .litematic and .schem files.
8. `mesh.py`, `render_mc.py`: make the lit render in Blender Cycles with Minecraft textures.

## WorldEdit (.schem)

`dota2_map.schem` is a Sponge Schematic v3 file for WorldEdit / FastAsyncWorldEdit 1.21.11. It contains the same build. Put it in `plugins/WorldEdit/schematics/` (or `config/worldedit/schematics/` for the mod), then run:

```
//schem load dota2_map
//paste -a
```

Use FAWE for the paste: the build has 5.26 million blocks.

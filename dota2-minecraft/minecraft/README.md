# Dota 2 map in Minecraft 1.21.11

`dota2_map.litematic` is a Litematica schematic for Minecraft 1.21.11 (DataVersion 4667).

- Size: 956 × 111 × 1004 blocks (X × Y × Z), 1.85 blocks per metre of the original map.
- About 5.4 million blocks, 257 block types, 818 block states. Every state was checked against the 1.21.11 block list.
- Orientation: the Radiant base is at small X / large Z (south-west), and the Dire base is at large X / small Z (north-east).

## What's in it

- Terrain:
  - Radiant: grass, podzol, moss and paths (dirt_path, gravel, coarse dirt).
  - Dire: coarse dirt, packed mud, tuff, lava and magma.
  - Cliffs are made of stone, tuff, deepslate and cobblestone, chosen by the texture colour.
- River:
  - water whose depth grows towards the middle;
  - bed of mud, clay, gravel and sand;
  - seagrass, tall seagrass, sea pickles and lily pads.
- Trees (about 300k log blocks and 517k leaf blocks), with log and leaf types chosen per Dota tree kind:
  - pine → spruce;
  - oak → oak, dark oak, azalea;
  - blossom → cherry;
  - Dire trees → dark oak, pale oak, nether wart;
  - bamboo → bamboo.
- Tree details:
  - thin branches made of fences that connect to each other;
  - buttons on trunks;
  - twig fences;
  - cave vines with glow berries, pale hanging moss, hanging roots and spore blossoms;
  - leaf litter and pale moss carpet under the canopy.
- Buildings (towers, barracks, fountains, shops, camps):
  - stairs on slopes and roofs;
  - walls and fences on thin posts, with lanterns on top;
  - chains with hanging lanterns (copper, regular and soul) under overhangs;
  - lit candles and torches (copper and soul);
  - pale_oak_shelf / dark_oak_shelf for the shops, decorated pots, barrels and amethyst.
- Grass:
  - short and tall grass, ferns, bushes, wildflowers, pink petals and flowers coloured from the map;
  - firefly bushes by the water;
  - dry grass and dead bushes in the Dire.

## How to use it

Put the file in `.minecraft/schematics/` (Litematica + MaLiLib for 1.21.11). Paste it on a flat world with `/litematica` or with the Easy Place / Paste mode. The schematic is large, so on a server raise the paste limits or paste in parts.

## Scripts (`scripts/`)

1. `export_tris.py` (Blender): exports the map's triangles from the glTF.
2. `voxelize.py`, `aggregate.py`: voxelize the triangles and sample texture colours.
3. `palette.py`: computes average colours from the real 1.21.11 textures.
4. `build.py`, `build2.py`: choose the blocks and add the details.
5. `write_lit.py`: writes the .litematic file.
6. `mesh.py`, `render_mc.py`: make the lit render in Blender Cycles with Minecraft textures.

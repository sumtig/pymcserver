"""Block ID groups and lookup tables."""

import base64
import os

SERVER_NAME = "Python Server"
SERVER_DESCRIPTION = "Hosted in Python"

# Automatically load favicon.png from the root directory if present
FAVICON_BASE64 = None
_favicon_path = os.path.join(os.path.dirname(__file__), "..", "favicon.png")
if os.path.exists(_favicon_path):
    with open(_favicon_path, "rb") as _f:
        FAVICON_BASE64 = "data:image/png;base64," + base64.b64encode(_f.read()).decode("utf-8")

SPAWN_X = 8.0

SPAWN_Y = 46.0

SPAWN_Z = 8.0

DOOR_BLOCK_IDS = {64, 71, 193, 194, 195, 196, 197}

WOODEN_DOOR_IDS = DOOR_BLOCK_IDS - {71}          # iron door can't be opened by hand

DOOR_ITEM_TO_BLOCK = {
    324: 64,   # Oak Door
    330: 71,   # Iron Door
    427: 193,  # Spruce Door
    428: 194,  # Birch Door
    429: 195,  # Jungle Door
    430: 196,  # Dark Oak Door
    431: 197   # Acacia Door
}

FLUID_ITEM_TO_BLOCK = {
    326: 8,    # Water Bucket -> Flowing Water
    327: 10    # Lava Bucket -> Flowing Lava
}

# Items whose item ID differs from the block ID (everything else <= 255 is a plain ItemBlock)
ITEM_TO_BLOCK = {**DOOR_ITEM_TO_BLOCK, **FLUID_ITEM_TO_BLOCK, 331: 55, 356: 93, 404: 149}

FLUID_BLOCK_IDS = {8, 9, 10, 11}

TRAPDOOR_IDS = {96, 167}                          # 96 oak, 167 iron

PRESSURE_PLATE_IDS = {70, 72, 147, 148}           # stone, wood, gold(light), iron(heavy)

BUTTON_IDS = {77, 143}

FENCE_GATE_IDS = {107, 183, 184, 185, 186, 187}

TORCH_IDS = {50, 75, 76}

STAIR_IDS = {53, 67, 108, 109, 114, 128, 134, 135, 136, 156, 163, 164, 180}

SLAB_IDS = {44, 126}

LOG_IDS = {17, 162}

FACING_PLAYER_IDS = {23, 54, 61, 130, 146, 158}   # chests, furnace, dispenser, dropper...

# Blocks whose GUI this server doesn't implement - they still swallow the click like in vanilla
GUI_BLOCK_IDS = {23, 25, 54, 58, 61, 62, 84, 116, 117, 130, 137, 138, 145, 146, 154, 158}

# Right-click on these activates them instead of placing a block (unless sneaking with an item)
USABLE_BLOCK_IDS = (WOODEN_DOOR_IDS | {96} | FENCE_GATE_IDS | BUTTON_IDS |
                    {69, 93, 94, 149, 150} | GUI_BLOCK_IDS)

REPLACEABLE_IDS = {0, 8, 9, 10, 11, 31, 32, 51, 78, 106, 175}

NON_SOLID_IDS = ({0, 6, 8, 9, 10, 11, 26, 27, 28, 30, 31, 32, 34, 37, 38, 39, 40, 51, 55, 59,
                  63, 65, 66, 68, 78, 83, 90, 93, 94, 104, 105, 106, 111, 115, 131, 132, 140,
                  141, 142, 149, 150, 157, 171, 175}
                 | DOOR_BLOCK_IDS | PRESSURE_PLATE_IDS | BUTTON_IDS | TORCH_IDS
                 | TRAPDOOR_IDS | {69})

FLOOR_ATTACHED_IDS = PRESSURE_PLATE_IDS | {55, 27, 28, 66, 157, 93, 94, 149, 150}

WALL_ATTACHED_IDS = TORCH_IDS | BUTTON_IDS | {69}

SIDE_OFFSETS = {1: (-1, 0, 0), 2: (1, 0, 0), 3: (0, 0, -1), 4: (0, 0, 1)}

LADDER_OFFSETS = {2: (0, 0, 1), 3: (0, 0, -1), 4: (1, 0, 0), 5: (-1, 0, 0)}

# look index (0=S,1=W,2=N,3=E) -> piston/chest facing (faces the player)
FACING_TOWARD_PLAYER = {0: 2, 1: 5, 2: 3, 3: 4}

# look index -> stair meta (0=E,1=W,2=S,3=N, ascending in look direction)
STAIR_META = {0: 2, 1: 1, 2: 3, 3: 0}

# look index -> trapdoor meta when placed on top/bottom (0=N,1=S,2=W,3=E, opposite of look)
TRAPDOOR_FLOOR_META = {0: 0, 1: 3, 2: 1, 3: 2}

SIDE_FACE_TO_ATTACH_META = {2: 4, 3: 3, 4: 2, 5: 1}   # clicked face -> torch/lever/button meta

NEIGHBOR_OFFSETS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

    # GUI blocks: click is swallowed, nothing else to do (no windows implemented)

DOUBLE_SLAB_OF = {44: 43, 126: 125}   # single slab block -> double slab block

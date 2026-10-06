"""Chunk data generation."""

def generate_chunk_section_data():
    section_blocks = bytearray(4096 * 2)

    for sec_y in range(16):
        world_y = 32 + sec_y
        for z in range(16):
            for x in range(16):
                index = (sec_y * 256 + z * 16 + x) * 2

                if world_y == 32:
                    block_id = 7   # Bedrock at Y=32
                elif 33 <= world_y <= 41:
                    block_id = 1   # Stone
                elif 42 <= world_y <= 44:
                    block_id = 3   # Dirt
                elif world_y == 45:
                    block_id = 2   # Grass Block at Y=45
                else:
                    block_id = 0   # Air above Y=45

                val = block_id << 4
                section_blocks[index] = val & 0xFF
                section_blocks[index+1] = (val >> 8) & 0xFF

    block_light = b'\xff' * 2048
    sky_light = b'\xff' * 2048
    biomes = b'\x01' * 256

    return bytes(section_blocks) + block_light + sky_light + biomes

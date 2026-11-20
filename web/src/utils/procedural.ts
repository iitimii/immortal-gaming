/**
 * Procedural generation for terrain
 * Avoids the visual clutter of pure randomness
 */

/**
 * Coordinate-based pseudo-random number generator
 * Returns a float in [0, 1]
 */
function random(x: number, y: number): number {
    const dot = x * 12.9898 + y * 78.233;
    const sin = Math.sin(dot);
    return (sin * 43758.5453) % 1; // frac
}

/**
 * Get a tile variant index using noise clustering
 * 
 * Algorithm:
 * 1. Two sine waves produce low-frequency noise (biome feel), so neighboring tiles tend to pick similar variants.
 * 2. High-frequency hash jitter is added so textures are not rigid or show obvious artificial ripples.
 * 3. Result: variants form natural "patches" on the map instead of random noise.
 * 
 * @param x Map X coordinate
 * @param y Map Y coordinate
 * @param count Number of variants (e.g. 9)
 * @param startIndex First variant index, defaults to 0
 * @returns Integer index from startIndex to startIndex + count - 1
 */
export function getClusteredTileVariant(x: number, y: number, count: number, startIndex: number = 0): number {
    if (count <= 1) return startIndex;

    // 1. Low-frequency (large-scale) noise
    // Sets the dominant look of an area. Smaller scale means larger patches.
    // 0.15 means a full period of about 2PI / 0.15 ~= 40 tiles;
    // visually a distinct "cluster" spans roughly 10-20 tiles.
    const scale = 0.15;
    
    // Two waves with different frequency and direction break up perfect diagonals
    const lowFreqNoise = Math.sin(x * scale + y * scale * 0.5) + 
                         Math.cos(y * scale * 0.8 - x * scale * 0.3);
    
    // lowFreqNoise is roughly [-2, 2]; normalize to [0, 1]
    const normalizedNoise = (lowFreqNoise + 2) / 4;

    // 2. High-frequency jitter
    // Low-frequency noise alone changes variants rigidly, like contour lines (1->2->3...).
    // Jitter interleaves the edges and adds some variety within a cluster.
    // range: [-0.5, 0.5]
    const noiseVal = Math.abs(random(x, y)); // 0~1
    const jitter = (noiseVal - 0.5) * 0.5;   // Strength 0.5

    // 3. Combine
    let finalValue = normalizedNoise + jitter;
    
    // Clamp to [0, 1]
    finalValue = Math.max(0, Math.min(1, finalValue));

    // 4. Map to [startIndex, startIndex + count - 1]
    let index = Math.floor(finalValue * count) + startIndex;
    
    // Bounds guard (against floating-point overflow)
    const maxIndex = startIndex + count - 1;
    if (index > maxIndex) index = maxIndex;
    if (index < startIndex) index = startIndex;

    return index;
}


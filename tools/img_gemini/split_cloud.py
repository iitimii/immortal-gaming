import os
import numpy as np
from PIL import Image, ImageFilter, ImageChops

def split_cloud_smart():
    input_path = os.path.join(os.path.dirname(__file__), 'origin', 'cloud.jpg')
    output_dir = os.path.join(os.path.dirname(__file__), 'clouds')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Processing {input_path}...")
    
    try:
        img = Image.open(input_path).convert("RGBA")
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    # 1. Smart background color sampling
    # Use pixels from all four image edges to estimate the background; more robust than a single corner
    width, height = img.size
    # Extract the top, bottom, left and right edge pixels
    top_edge = np.array(img.crop((0, 0, width, 1)))
    bottom_edge = np.array(img.crop((0, height-1, width, height)))
    left_edge = np.array(img.crop((0, 0, 1, height)))
    right_edge = np.array(img.crop((width-1, 0, width, height)))
    
    # Combine edge pixels
    edges = np.concatenate([
        top_edge.reshape(-1, 4), 
        bottom_edge.reshape(-1, 4), 
        left_edge.reshape(-1, 4), 
        right_edge.reshape(-1, 4)
    ])
    
    # Mean (and spread) of the background color, used to set the tolerance
    bg_mean = np.mean(edges, axis=0)
    print(f"Smart sampled background color (RGBA): {bg_mean}")

    # 2. HSV separation
    # Convert to HSV and use saturation (S) and value (V) to tell clouds (usually low S, high V) from the dark background (usually high S, low V)
    hsv_img = img.convert("HSV")
    hsv_data = np.array(hsv_img)
    rgb_data = np.array(img)
    
    # Extract channels
    H, S, V = hsv_data[:,:,0], hsv_data[:,:,1], hsv_data[:,:,2]
    R, G, B = rgb_data[:,:,0], rgb_data[:,:,1], rgb_data[:,:,2]
    
    # Euclidean RGB distance to the mean background color
    # Only compare the first three (RGB) channels
    diff_r = R.astype(float) - bg_mean[0]
    diff_g = G.astype(float) - bg_mean[1]
    diff_b = B.astype(float) - bg_mean[2]
    rgb_distance = np.sqrt(diff_r**2 + diff_g**2 + diff_b**2)
    
    # Thresholds
    # RGB tolerance: allow some color variation in the background
    rgb_tolerance = 60.0 
    
    # HSV hints:
    # The background is usually dark purple; clouds (white/gray) must be protected and are characterized by low saturation
    # A pixel somewhat far from the background color but highly saturated and purplish is probably still background (gradient area)
    # A pixel close to the background color but with very low saturation (a gray cloud edge) should be kept
    
    # Build the alpha mask (0 = fully transparent/background, 255 = fully opaque/cloud)
    # Initial mask: the closer to the background color, the lower the alpha
    alpha_mask = np.zeros_like(H, dtype=np.float32)
    
    # Core logic:
    # 1. Mostly background: RGB distance < tolerance
    # 2. Soft edges: use a smooth falloff in edge areas instead of a hard cut
    
    # Normalized distance; smaller means closer to the background
    normalized_dist = np.clip(rgb_distance / rgb_tolerance, 0, 1)
    
    # Simple linear mapping: smaller distance (background) means lower alpha (transparent)
    # Apply smoothstep for a more natural transition: 3x^2 - 2x^3
    alpha_mask = np.clip((normalized_dist - 0.2) / 0.6, 0, 1) # transition between 0.2 and 0.8
    alpha_mask = alpha_mask * alpha_mask * (3 - 2 * alpha_mask)
    
    # 3. Cloud core protection
    # Very bright (high V) and low-saturation (low S) pixels are forced to be cloud (opaque)
    # Assumes clouds are white and the background is dark
    is_cloud_core = (V > 150) & (S < 60) 
    alpha_mask[is_cloud_core] = 1.0
    
    # 4. Convert back to 0-255 and feather
    final_alpha = (alpha_mask * 255).astype(np.uint8)
    
    # Create the mask image
    mask_img = Image.fromarray(final_alpha, mode='L')
    
    # Matte refinement
    # Slightly blur the mask to remove jagged edges
    mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    # Apply the processed alpha channel back to the image
    r, g, b, a = img.split()
    img_transparent = Image.merge('RGBA', (r, g, b, mask_img))

    # Grid splitting logic is unchanged
    width, height = img.size
    cell_width = width // 3
    cell_height = height // 3
    
    count = 0
    for r in range(3):
        for c in range(3):
            left = c * cell_width
            top = r * cell_height
            right = left + cell_width
            bottom = top + cell_height
            
            cell = img_transparent.crop((left, top, right, bottom))
            
            output_filename = f"cloud_{count}.png"
            output_path = os.path.join(output_dir, output_filename)
            cell.save(output_path)
            print(f"Saved {output_path}")
            count += 1
            
    print("Smart split done!")

if __name__ == "__main__":
    split_cloud_smart()

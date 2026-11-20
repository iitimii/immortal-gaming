import os
from PIL import Image
import glob

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def split_image(image_path):
    try:
        img = Image.open(image_path)
        w, h = img.size
        
        # Split into a 2x2 grid:
        # always cut into 4 pieces regardless of the source size
        # (rather than forcing a resize to 128x128 = 64*2 first; TILE_SIZE used to be 64).
        # Keep the source proportions; ideally the source is square.
        
        # To preserve sharpness, split at the source resolution; the frontend scales to TILE_SIZE when rendering.
        # Only the 2x2 logical layout matters.
        
        half_w = w // 2
        half_h = h // 2
        
        # 0: TL, 1: TR, 2: BL, 3: BR
        pieces = [
            (0, 0, half_w, half_h),
            (half_w, 0, w, half_h),
            (0, half_h, half_w, h),
            (half_w, half_h, w, h)
        ]
        
        base_name, ext = os.path.splitext(image_path)
        
        generated_files = []
        for i, box in enumerate(pieces):
            # Crop
            piece = img.crop(box)
            
            # Save as _0, _1, _2, _3
            # Always save as PNG to support transparency and keep outputs uniform
            # (JPG sources have no alpha anyway; only cities are JPG, sects are already PNG).
            
            # Decision: always output .png so the frontend loading logic stays uniform
            save_path = f"{base_name}_{i}.png"
            piece.save(save_path, "PNG")
            generated_files.append(save_path)
            
        print(f"Split {os.path.basename(image_path)} -> 4 parts")
        return generated_files
        
    except Exception as e:
        print(f"Error splitting {image_path}: {e}")
        return []

def main():
    # 1. Sects
    sect_files = glob.glob(os.path.join(ASSETS_DIR, "sects", "*.png"))
    # Filter out already split files (ending with _0.png, etc)
    sect_files = [f for f in sect_files if not (f.endswith("_0.png") or f.endswith("_1.png") or f.endswith("_2.png") or f.endswith("_3.png"))]
    
    for f in sect_files:
        split_image(f)
        
    # 2. Cities
    city_files = glob.glob(os.path.join(ASSETS_DIR, "cities", "*.*"))
    city_files = [f for f in city_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    city_files = [f for f in city_files if not (f.split('.')[0].endswith("_0") or f.split('.')[0].endswith("_1"))] # Simple check
    
    for f in city_files:
        split_image(f)

    # 3. Special Tiles (Cave, Ruin)
    # cave.png, ruin.png (older code used both ruins.png and ruin.png; both are handled here)
    # Check files under assets/tiles
    special_names = ['cave', 'ruin', 'ruins']
    for name in special_names:
        path = os.path.join(ASSETS_DIR, "tiles", f"{name}.png")
        if os.path.exists(path):
            split_image(path)
        else:
            # Try jpg just in case?
            pass

if __name__ == "__main__":
    main()


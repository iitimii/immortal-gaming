"""
Split 3x3 grid images into 9 separate images.
Divider positions are detected from per-row/column pixel variance.
"""

import os
from pathlib import Path
import numpy as np
from PIL import Image


def find_split_line(variance: np.ndarray, start: int, end: int) -> tuple[int, int]:
    """
    Find the contiguous region with minimal variance within the given range (the divider position).
    Returns (line_start, line_end).
    """
    # Find the position of the minimum within the range
    region = variance[start:end]
    min_idx = start + np.argmin(region)
    min_val = variance[min_idx]
    
    # Expand on both sides until the variance rises clearly (above 3x the minimum or an absolute threshold)
    threshold = max(min_val * 3, 50)
    
    line_start = min_idx
    while line_start > 0 and variance[line_start - 1] < threshold:
        line_start -= 1
    
    line_end = min_idx
    while line_end < len(variance) - 1 and variance[line_end + 1] < threshold:
        line_end += 1
    
    return line_start, line_end + 1  # Return a half-open interval [start, end)


def find_split_line_by_gradient(gray: np.ndarray, axis: int, start: int, end: int, is_bright_line: bool) -> tuple[int, int]:
    """
    Detect divider boundaries from abrupt brightness gradients.
    axis: 0 = detect horizontal lines, 1 = detect vertical lines
    is_bright_line: True = bright divider (e.g. white), False = dark divider (e.g. black)
    """
    if axis == 0:
        means = np.mean(gray, axis=1)  # Mean brightness per row
    else:
        means = np.mean(gray, axis=0)  # Mean brightness per column
    
    # Brightness difference between adjacent rows/columns (gradient)
    gradient = np.diff(means)
    
    # Find the divider center: the brightness extremum within the range
    region = means[start:end]
    if is_bright_line:
        center_idx = start + np.argmax(region)  # Bright line: take the brightest point
    else:
        center_idx = start + np.argmin(region)  # Dark line: take the darkest point
    
    # Search left from the center for the boundary: where the gradient jumps (abrupt brightness change)
    line_start = center_idx
    for i in range(center_idx - 1, max(0, center_idx - 30), -1):
        # Bright line: gradient > 0 at the boundary (dark to bright)
        # Dark line: gradient < 0 at the boundary (bright to dark)
        if is_bright_line and gradient[i] > 3:
            line_start = i + 1
            break
        elif not is_bright_line and gradient[i] < -3:
            line_start = i + 1
            break
        line_start = i
    
    # Search right from the center for the boundary
    line_end = center_idx
    for i in range(center_idx, min(len(gradient), center_idx + 30)):
        if is_bright_line and gradient[i] < -3:
            line_end = i + 1
            break
        elif not is_bright_line and gradient[i] > 3:
            line_end = i + 1
            break
        line_end = i + 1
    
    return line_start, line_end


def detect_split_lines_forest(image: Image.Image) -> tuple[list, list]:
    """Special handling for the wide white dividers in forest."""
    gray = np.array(image.convert('L'), dtype=np.float32)
    h, w = gray.shape
    
    h_line1 = find_split_line_by_gradient(gray, 0, h // 4, h // 2 + h // 8, is_bright_line=True)
    h_line2 = find_split_line_by_gradient(gray, 0, h // 2 + h // 8, 3 * h // 4, is_bright_line=True)
    
    v_line1 = find_split_line_by_gradient(gray, 1, w // 4, w // 2 + w // 8, is_bright_line=True)
    v_line2 = find_split_line_by_gradient(gray, 1, w // 2 + w // 8, 3 * w // 4, is_bright_line=True)
    
    return [h_line1, h_line2], [v_line1, v_line2]


def detect_split_lines_snow_mountain(image: Image.Image) -> tuple[list, list]:
    """Special handling for the thin black dividers in snow_mountain."""
    gray = np.array(image.convert('L'), dtype=np.float32)
    h, w = gray.shape
    
    h_line1 = find_split_line_by_gradient(gray, 0, h // 4, h // 2 + h // 8, is_bright_line=False)
    h_line2 = find_split_line_by_gradient(gray, 0, h // 2 + h // 8, 3 * h // 4, is_bright_line=False)
    
    v_line1 = find_split_line_by_gradient(gray, 1, w // 4, w // 2 + w // 8, is_bright_line=False)
    v_line2 = find_split_line_by_gradient(gray, 1, w // 2 + w // 8, 3 * w // 4, is_bright_line=False)
    
    return [h_line1, h_line2], [v_line1, v_line2]


def detect_split_lines(image: Image.Image) -> tuple[list, list]:
    """
    Detect the positions of the horizontal and vertical dividers.
    Returns (h_lines, v_lines), each being [(start1, end1), (start2, end2)].
    """
    gray = np.array(image.convert('L'), dtype=np.float32)
    h, w = gray.shape
    
    # Variance per row
    row_variance = np.var(gray, axis=1)
    
    # Variance per column
    col_variance = np.var(gray, axis=0)
    
    # Smooth to reduce the effect of noise
    kernel_size = 3
    row_variance = np.convolve(row_variance, np.ones(kernel_size)/kernel_size, mode='same')
    col_variance = np.convolve(col_variance, np.ones(kernel_size)/kernel_size, mode='same')
    
    # Look for the first divider around 1/4-1/2 and the second around 1/2-3/4
    h_line1 = find_split_line(row_variance, h // 4, h // 2 + h // 8)
    h_line2 = find_split_line(row_variance, h // 2 + h // 8, 3 * h // 4)
    
    v_line1 = find_split_line(col_variance, w // 4, w // 2 + w // 8)
    v_line2 = find_split_line(col_variance, w // 2 + w // 8, 3 * w // 4)
    
    return [h_line1, h_line2], [v_line1, v_line2]


def split_image(image: Image.Image, h_lines: list, v_lines: list) -> list[Image.Image]:
    """
    Split the image into 9 tiles based on the divider positions.
    """
    w, h = image.size
    
    # Compute split bounds: [0, line1_start, line1_end, line2_start, line2_end, total]
    y_bounds = [0, h_lines[0][0], h_lines[0][1], h_lines[1][0], h_lines[1][1], h]
    x_bounds = [0, v_lines[0][0], v_lines[0][1], v_lines[1][0], v_lines[1][1], w]
    
    tiles = []
    # Take regions at indexes 0, 2, 4 (skipping divider regions 1, 3)
    for row_idx in [0, 2, 4]:
        for col_idx in [0, 2, 4]:
            left = x_bounds[col_idx]
            right = x_bounds[col_idx + 1]
            top = y_bounds[row_idx]
            bottom = y_bounds[row_idx + 1]
            
            tile = image.crop((left, top, right, bottom))
            tiles.append(tile)
    
    return tiles


def process_image(input_path: Path, output_dir: Path):
    """Process a single image."""
    image = Image.open(input_path)
    name = input_path.stem
    
    # Special images use dedicated detection methods
    if name == 'forest':
        h_lines, v_lines = detect_split_lines_forest(image)
    elif name == 'snow_mountain':
        h_lines, v_lines = detect_split_lines_snow_mountain(image)
    else:
        h_lines, v_lines = detect_split_lines(image)
    
    print(f"{name}: horizontal dividers {h_lines}, vertical dividers {v_lines}")
    
    # Split
    tiles = split_image(image, h_lines, v_lines)
    
    # Save
    for i, tile in enumerate(tiles):
        output_path = output_dir / f"{name}_{i}.png"
        tile.save(output_path)
        print(f"  Saved: {output_path.name} ({tile.size[0]}x{tile.size[1]})")


def main():
    script_dir = Path(__file__).parent
    input_dir = script_dir / "origin2"
    output_dir = script_dir / "split2"
    
    output_dir.mkdir(exist_ok=True)
    
    # Supported image formats
    extensions = {'.jpg', '.jpeg', '.png'}
    
    for path in sorted(input_dir.iterdir()):
        if path.suffix.lower() in extensions:
            process_image(path, output_dir)
    
    print(f"\nDone! Output directory: {output_dir}")


if __name__ == "__main__":
    main()


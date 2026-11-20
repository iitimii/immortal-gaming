import math

def chebyshev_distance(p1: tuple[int, int], p2: tuple[int, int]) -> int:
    """
    Chebyshev distance: max(|x1-x2|, |y1-y2|)
    For grid maps that allow diagonal movement.
    """
    return max(abs(p1[0] - p2[0]), abs(p1[1] - p2[1]))

def manhattan_distance(p1: tuple[int, int], p2: tuple[int, int]) -> int:
    """
    Manhattan distance: |x1-x2| + |y1-y2|
    For grid maps that only allow four-directional movement.
    """
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def euclidean_distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    """
    Euclidean distance: sqrt((x1-x2)^2 + (y1-y2)^2)
    """
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


from __future__ import annotations


def clamp_manhattan_with_diagonal_priority(dx: int, dy: int, step: int) -> tuple[int, int]:
    """
    Clip (dx, dy) so the Manhattan step doesn't exceed the given step, preferring diagonal moves.

    Rules:
    - The returned (mx, my) satisfies |mx| + |my| <= step
    - Each axis doesn't exceed the original target: |mx| <= |dx|, |my| <= |dy|
    - Diagonal steps are allocated first (using 1 step on both x and y), then the remaining steps go to the axis with more remaining distance
    - The original direction (sign) is preserved
    """
    if step <= 0 or (dx == 0 and dy == 0):
        return 0, 0

    abs_dx = abs(dx)
    abs_dy = abs(dy)
    sign_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sign_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

    # The usable budget doesn't exceed the required Manhattan distance
    budget = min(step, abs_dx + abs_dy)

    # Allocate as many diagonal steps as possible first: each costs 2 budget points
    diagonal_steps = min(min(abs_dx, abs_dy), budget // 2)
    move_x = diagonal_steps
    move_y = diagonal_steps

    remaining = budget - 2 * diagonal_steps

    # If budget remains, give it to the axis with more remaining distance
    rem_x = abs_dx - move_x
    rem_y = abs_dy - move_y
    if remaining > 0:
        if rem_x >= rem_y:
            add_x = min(remaining, rem_x)
            move_x += add_x
            remaining -= add_x
        if remaining > 0:
            add_y = min(remaining, rem_y)
            move_y += add_y

    return move_x * sign_x, move_y * sign_y



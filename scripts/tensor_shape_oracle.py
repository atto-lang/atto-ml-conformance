"""Independent coordinate-based dense tensor oracle.

This is intentionally different from the pure-Oreslang linear-offset kernel:
coordinates are enumerated using itertools.product, then mapped to row-major
storage. This test oracle never executes a guest compiler.
"""
from __future__ import annotations

import itertools
import math


class ShapeError(ValueError):
    pass


def extent_product(shape):
    if not isinstance(shape, list) or len(shape) > 8:
        raise ShapeError("invalid tensor rank")
    if not all(type(d) is int and 0 <= d <= 10000 for d in shape):
        raise ShapeError("invalid tensor extent")
    product = math.prod(shape)
    if product > 10000:
        raise ShapeError("tensor exceeds fixture element budget")
    return product


def coordinates(shape):
    extent_product(shape)
    return itertools.product(*(range(d) for d in shape))


def position(shape, coords):
    if len(shape) != len(coords):
        raise ShapeError("rank mismatch")
    offset = 0
    for dim, coord in zip(shape, coords):
        if not 0 <= coord < dim:
            raise ShapeError("coordinate out of bounds")
        offset = offset * dim + coord
    return offset


def broadcast_shape(a, b):
    extent_product(a)
    extent_product(b)
    result = []
    for left, right in itertools.zip_longest(reversed(a), reversed(b), fillvalue=1):
        if left != right and left != 1 and right != 1:
            raise ShapeError("broadcast mismatch")
        result.append(right if left == 1 else left)
    result.reverse()
    extent_product(result)
    return result


def input_position(input_shape, output_coords):
    suffix = output_coords[len(output_coords)-len(input_shape):] if input_shape else ()
    return position(input_shape, tuple(0 if n == 1 else c
                                       for n, c in zip(input_shape, suffix)))


def broadcast_add(left_shape, left_values, right_shape, right_values):
    if extent_product(left_shape) != len(left_values):
        raise ShapeError("left shape/storage mismatch")
    if extent_product(right_shape) != len(right_values):
        raise ShapeError("right shape/storage mismatch")
    out_shape = broadcast_shape(left_shape, right_shape)
    out_values = [
        left_values[input_position(left_shape, idx)] +
        right_values[input_position(right_shape, idx)]
        for idx in coordinates(out_shape)
    ]
    if not all(math.isfinite(v) for v in out_values):
        raise ShapeError("nonfinite broadcast output")
    return out_shape, out_values


def sum_to_shape(upstream_shape, upstream_values, target_shape):
    if extent_product(upstream_shape) != len(upstream_values):
        raise ShapeError("upstream shape/storage mismatch")
    if len(target_shape) > len(upstream_shape):
        raise ShapeError("target rank exceeds upstream")
    extent_product(target_shape)
    expanded = [1] * (len(upstream_shape) - len(target_shape)) + target_shape
    for source, target in zip(upstream_shape, expanded):
        if source != target and target != 1:
            raise ShapeError("invalid reduction target")
    buckets = [[] for _ in range(extent_product(target_shape))]
    for coords, value in zip(coordinates(upstream_shape), upstream_values):
        out_coords = tuple(0 if extent == 1 else coordinate
                           for extent, coordinate in
                           zip(expanded, coords))[-len(target_shape):] if target_shape else ()
        buckets[position(target_shape, out_coords)].append(value)
    values = [math.fsum(bucket) for bucket in buckets]
    if not all(math.isfinite(v) for v in values):
        raise ShapeError("nonfinite reduction result")
    return values

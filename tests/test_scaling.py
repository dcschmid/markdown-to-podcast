import os
import sys
import pytest

# Ensure project root is on sys.path so tests can import the module directly
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.image_utils import compute_contain_size


def test_compute_contain_size_happy_path():
    w, h = compute_contain_size(1000, 500, 720, 405, zoom=1.0)
    # source 2:1 into 16:9-ish area should fit by width
    assert w <= 720
    assert h <= 405
    assert w >= 2 and h >= 2


def test_compute_contain_size_very_tall():
    w, h = compute_contain_size(200, 1000, 720, 405, zoom=1.0)
    assert w <= 720
    assert h <= 405
    assert w >= 2 and h >= 2


def test_compute_contain_size_zero_src():
    w, h = compute_contain_size(0, 0, 720, 405)
    assert w == 2 and h == 2

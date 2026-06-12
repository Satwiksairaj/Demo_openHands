import pytest
from calculator import add, subtract, multiply, divide, percentage

def test_add():
    assert add(3, 2) == 5
    assert add(-1, -1) == -2
    assert add(0, 0) == 0


def test_subtract():
    assert subtract(3, 2) == 1
    assert subtract(-1, -1) == 0
    assert subtract(0, 3) == -3


def test_multiply():
    assert multiply(3, 2) == 6
    assert multiply(-1, 2) == -2
    assert multiply(0, 3) == 0


def test_divide():
    assert divide(6, 2) == 3
    assert divide(-4, 2) == -2
    with pytest.raises(ValueError):
        divide(5, 0)


def test_percentage():
    assert percentage(50, 100) == 50
    assert percentage(25, 200) == 50
    assert percentage(0, 100) == 0

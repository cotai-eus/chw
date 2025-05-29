"""
Simple unit test for basic functionality.
"""
import pytest

def test_simple_math():
    """Test basic math operations."""
    assert 1 + 1 == 2
    assert 2 * 3 == 6
    assert 10 / 2 == 5

def test_string_operations():
    """Test basic string operations."""
    text = "hello world"
    assert text.upper() == "HELLO WORLD"
    assert text.title() == "Hello World"
    assert len(text) == 11

def test_list_operations():
    """Test basic list operations."""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert test_list[0] == 1
    assert test_list[-1] == 5
    assert sum(test_list) == 15

@pytest.mark.parametrize("x,y,expected", [
    (1, 2, 3),
    (5, 5, 10),
    (10, -5, 5),
])
def test_addition_parametrized(x, y, expected):
    """Test addition with multiple parameters."""
    assert x + y == expected

class TestBasicClass:
    """Test basic class functionality."""
    
    def test_class_instantiation(self):
        """Test creating a simple class."""
        
        class SimpleClass:
            def __init__(self, value):
                self.value = value
            
            def get_value(self):
                return self.value
        
        obj = SimpleClass(42)
        assert obj.get_value() == 42

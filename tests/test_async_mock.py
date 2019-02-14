import pytest

from . import AsyncMock


async def test_async_mock_no_return():
    foo = AsyncMock()
    assert await foo() is None


async def test_async_mock_single_return():
    foo = AsyncMock(return_value=1)
    assert await foo() == 1
    assert await foo() == 1


async def test_async_mock_multiple_returns():
    foo = AsyncMock(return_values=(1,2))
    assert await foo() == 1
    assert await foo() == 2


async def test_async_mock_raises():
    foo = AsyncMock(raises=Exception)
    with pytest.raises(Exception):
        await foo()

"""Pagination arithmetic. Pure logic — no database."""

from __future__ import annotations

import pytest

from app.schemas.common import PaginatedResponse, PaginationParams


def test_offset_is_derived_from_the_page():
    assert PaginationParams(page=1, page_size=20).offset == 0
    assert PaginationParams(page=3, page_size=20).offset == 40


def test_navigation_flags_on_a_middle_page():
    page = PaginatedResponse[int].build(
        [1, 2], total=45, params=PaginationParams(page=2, page_size=20)
    )
    assert page.total_pages == 3
    assert page.has_next is True
    assert page.has_previous is True


def test_last_page_has_no_next():
    page = PaginatedResponse[int].build(
        [1], total=41, params=PaginationParams(page=3, page_size=20)
    )
    assert page.total_pages == 3
    assert page.has_next is False


def test_empty_result_has_no_pages_and_no_navigation():
    page = PaginatedResponse[int].build([], total=0, params=PaginationParams())
    assert (page.total_pages, page.has_next, page.has_previous) == (0, False, False)


@pytest.mark.parametrize(("page", "page_size"), [(0, 20), (1, 0), (1, 100_000)])
def test_out_of_range_parameters_are_rejected(page: int, page_size: int):
    with pytest.raises(ValueError):
        PaginationParams(page=page, page_size=page_size)

"""Seitenverweise: ``app.py`` trägt die ``st.Page``-Objekte bei jedem Lauf ein, damit Seiten einander ansteuern können."""

from __future__ import annotations

import streamlit as st

PAGES: dict[str, object] = {}


def go(name: str) -> None:
    page = PAGES.get(name)
    if page is not None:
        st.switch_page(page)

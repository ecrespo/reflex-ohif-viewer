"""Shared chrome for the demo pages."""

from __future__ import annotations

import reflex as rx
from reflex_ohif_viewer import VERSIONS

NAV = [
    ("Overview", "/"),
    ("Native viewport", "/native"),
    ("MPR", "/mpr"),
    ("OHIF iframe", "/ohif"),
    ("Deploy OHIF", "/deploy"),
]


def nav_link(label: str, href: str) -> rx.Component:
    """Render one navigation link.

    Args:
        label: The visible text.
        href: The route.

    Returns:
        The link component.

    """
    return rx.link(
        label,
        href=href,
        padding="0.4rem 0.8rem",
        border_radius="6px",
        _hover={"background": rx.color("accent", 4)},
        color=rx.color("gray", 12),
        weight="medium",
        size="2",
    )


def page(title: str, subtitle: str, *children: rx.Component) -> rx.Component:
    """Wrap page content in the shared header and container.

    Args:
        title: The page heading.
        subtitle: One line of context under the heading.
        *children: The page body.

    Returns:
        The full page component.

    """
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("scan-line", size=20, color=rx.color("accent", 11)),
                rx.text("reflex-ohif-viewer", weight="bold", size="3"),
                rx.badge(f"Cornerstone3D {VERSIONS['cornerstone3d']}", variant="soft"),
                rx.badge(f"OHIF {VERSIONS['ohif_viewer']}", variant="soft"),
                spacing="2",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(*[nav_link(label, href) for label, href in NAV], spacing="1"),
            rx.color_mode.button(),
            width="100%",
            align="center",
            padding="0.75rem 1.25rem",
            border_bottom=f"1px solid {rx.color('gray', 5)}",
            position="sticky",
            top="0",
            background=rx.color("gray", 1),
            z_index="10",
        ),
        rx.vstack(
            rx.vstack(
                rx.heading(title, size="7"),
                rx.text(subtitle, color=rx.color("gray", 11), size="2"),
                spacing="1",
                align="start",
                width="100%",
            ),
            *children,
            spacing="5",
            padding="1.5rem",
            width="100%",
            max_width="1500px",
            margin="0 auto",
        ),
        min_height="100vh",
        background=rx.color("gray", 2),
    )


def panel(*children: rx.Component, **props) -> rx.Component:
    """A bordered content card.

    Args:
        *children: The card body.
        **props: Extra box props.

    Returns:
        The card component.

    """
    return rx.box(
        rx.vstack(*children, spacing="3", align="stretch", width="100%"),
        padding="1rem",
        border=f"1px solid {rx.color('gray', 5)}",
        border_radius="10px",
        background=rx.color("gray", 1),
        **props,
    )


def code_block(text: rx.Var | str, language: str = "bash") -> rx.Component:
    """A scrollable, copyable code block.

    Args:
        text: The code to show.
        language: Syntax highlighting language.

    Returns:
        The code block component.

    """
    return rx.box(
        rx.code_block(
            text,
            language=language,
            wrap_long_lines=True,
            can_copy=True,
            font_size="0.78rem",
        ),
        max_height="340px",
        overflow="auto",
        width="100%",
    )

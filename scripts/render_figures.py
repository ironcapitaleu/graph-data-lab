"""Draws the figures of the documentation from the data in Neo4j.

Each figure is one Cypher query that returns paths. The script lays the nodes of the paths out
as a tree from left to right and writes an SVG file to `docs/images/`. The Markdown files show
the same query next to the figure, so a reader can run it in the Neo4j Browser.

Run it from the repo root after you load the stores:

    uv run python -m scripts.load_stores
    uv run python -m scripts.render_figures
"""

from dataclasses import dataclass
from html import escape
from typing import LiteralString

from neo4j import GraphDatabase
from neo4j.graph import Node, Path, Relationship

from scripts.load_stores import NEO4J_AUTH, NEO4J_URI, ROOT

IMAGES = ROOT / "docs" / "images"

RADIUS = 38
ROW_GAP = 112
MARGIN = 80
PARALLEL_EDGE_GAP = 34
LABEL_POSITION = 0.6

EDGE_COLOR = "#8a8f98"
"""A gray that is readable on the light and on the dark theme of GitHub."""

NODE_COLORS: dict[str, str] = {
    "Company": "#f4c5b8",
    "Identifier": "#d9c8f5",
    "Registrant": "#9dc25a",
    "FiscalYear": "#d8b5d8",
    "FiscalQuarter": "#d4a537",
    "Filing": "#8fe9fb",
    "Exchange": "#f7e08a",
    "Industry": "#f0b672",
}
"""Fill color per node label, close to the colors of the Neo4j Browser."""


@dataclass(frozen=True)
class Figure:
    """One figure of the documentation.

    Attributes:
        name: The file name without extension.
        query: A Cypher query that returns paths in the column `p`.
        root: The label and the caption title of the node on the left edge.
        layer_gap: The horizontal distance between two layers, in pixels. A figure with long
            edge labels needs more.
    """

    name: str
    query: LiteralString
    root: tuple[str, str]
    layer_gap: int = 250


FIGURES = (
    Figure(
        name="company-identity",
        query="""
            MATCH p = (:Company {name: 'Apple Inc.'})-[:HAS_IDENTIFIER|REGISTERED_WITH]->()
            RETURN p
        """,
        root=("Company", "Apple Inc."),
    ),
    Figure(
        name="sec-fiscal-tree",
        query="""
            MATCH p = (:Company {name: 'Apple Inc.'})-[:REGISTERED_WITH]->
                      (:Registrant {source: 'SEC'})-[:HAS_FISCAL_YEAR]->(:FiscalYear)
                      -[:HAS_QUARTER]->(:FiscalQuarter)
            RETURN p
            UNION
            MATCH (:Registrant {source: 'SEC', native_id: '0000320193'})-[:HAS_FILING]->(f:Filing)
            MATCH p = (f)-[:REPORTS_ON]->()
            RETURN p
        """,
        root=("Company", "Apple Inc."),
    ),
    Figure(
        name="mislabelled-filing",
        query="""
            MATCH p = (:Company {name: 'AES CORP'})-[:REGISTERED_WITH]->
                      (g:Registrant {source: 'SEC'})-[:HAS_FISCAL_YEAR]->(:FiscalYear)
                      -[:HAS_QUARTER]->(:FiscalQuarter)
            RETURN p
            UNION
            MATCH (g:Registrant {source: 'SEC', registered_name: 'AES CORP'})
            MATCH p = (g)-[:HAS_FILING]->(f:Filing)
            WHERE NOT EXISTS { (f)-[:REPORTS_ON]->() }
            RETURN p
            UNION
            MATCH (:Registrant {source: 'SEC', registered_name: 'AES CORP'})-[:HAS_FILING]->(f)
            MATCH p = (f)-[:REPORTS_ON]->()
            RETURN p
        """,
        root=("Company", "AES CORP"),
    ),
    Figure(
        name="ownership-claims",
        query="""
            MATCH p = (:Company)-[:SUBSIDIARY_OF|OWNS_STAKE_IN]->(:Company)
            RETURN p
        """,
        root=("Company", "Alpha Holdings Inc"),
        layer_gap=390,
    ),
)


@dataclass
class Placed:
    """A node with its caption and its position in the figure.

    Attributes:
        node: The node from Neo4j.
        title: The text inside the circle.
        detail: The text below the circle.
        x: The horizontal position of the center.
        y: The vertical position of the center.
    """

    node: Node
    title: str
    detail: str
    x: float = 0.0
    y: float = 0.0


def main() -> None:
    """Runs the query of each figure and writes its SVG file."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    with driver.session() as session:
        for figure in FIGURES:
            paths: list[Path] = [record["p"] for record in session.run(figure.query)]
            (IMAGES / f"{figure.name}.svg").write_text(svg(figure, paths))
            print(f"Wrote docs/images/{figure.name}.svg")
    driver.close()


def svg(figure: Figure, paths: list[Path]) -> str:
    placed = {
        node.element_id: Placed(node, *caption(node)) for path in paths for node in path.nodes
    }
    edges = list({edge.element_id: edge for path in paths for edge in path.relationships}.values())
    layout(figure, placed, edges)
    width = max(node.x for node in placed.values()) + MARGIN + RADIUS
    height = max(node.y for node in placed.values()) + MARGIN + RADIUS
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}"'
        f' width="{width:.0f}" height="{height:.0f}"'
        ' font-family="Helvetica, Arial, sans-serif">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"'
        f' markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{EDGE_COLOR}"/>'
        "</marker>",
        "</defs>",
        *edge_parts(placed, edges),
        *(node_part(node) for node in placed.values()),
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def caption(node: Node) -> tuple[str, str]:
    """Returns the text inside the circle of a node and the text below it."""
    label = next(iter(node.labels))
    match label:
        case "Company":
            return node["name"], node["company_id"]
        case "Identifier":
            return node["scheme"], node["value"]
        case "Registrant":
            return node["source"], node["native_id"]
        case "FiscalYear":
            return node["name"], f"{node['start_date']} to {node['end_date']}"
        case "FiscalQuarter":
            return node["name"], f"ends {node['end_date']} · {node['calendar_quarter']}"
        case "Filing":
            return node["form"], f"filed {node['filed_date']}"
        case _:
            return label, ""


def layout(figure: Figure, placed: dict[str, Placed], edges: list[Relationship]) -> None:
    """Places the nodes as a tree from left to right, with the root of the figure on the left.

    The tree follows the edges in both directions. A leaf takes the next free row. A node with
    children sits at the middle of its children.
    """
    neighbors: dict[str, set[str]] = {key: set() for key in placed}
    for edge in edges:
        start, end = endpoints(edge)
        neighbors[start].add(end)
        neighbors[end].add(start)
    root = next(
        key
        for key, node in placed.items()
        if figure.root == (next(iter(node.node.labels)), node.title)
    )
    next_row = 0

    def place(key: str, depth: int, seen: set[str]) -> None:
        nonlocal next_row
        seen.add(key)
        children = sorted(
            neighbors[key] - seen,
            key=lambda child: (
                sorted(placed[child].node.labels),
                placed[child].title,
                placed[child].detail,
            ),
        )
        rows = []
        for child in children:
            if child not in seen:
                place(child, depth + 1, seen)
                rows.append(placed[child].y)
        placed[key].x = MARGIN + RADIUS + depth * figure.layer_gap
        if rows:
            placed[key].y = (min(rows) + max(rows)) / 2
        else:
            placed[key].y = MARGIN + next_row * ROW_GAP
            next_row += 1

    place(root, 0, set())


def endpoints(edge: Relationship) -> tuple[str, str]:
    start, end = edge.start_node, edge.end_node
    if start is None or end is None:
        raise ValueError(f"The edge {edge.type} has no start or end node")
    return start.element_id, end.element_id


def edge_parts(placed: dict[str, Placed], edges: list[Relationship]) -> list[str]:
    """Draws each edge as a curve. Edges between the same two nodes bend away from each other."""
    groups: dict[frozenset[str], list[Relationship]] = {}
    for edge in sorted(edges, key=edge_label):
        groups.setdefault(frozenset(endpoints(edge)), []).append(edge)
    parts = []
    for group in groups.values():
        for index, edge in enumerate(group):
            start, end = (placed[key] for key in endpoints(edge))
            # The bend is measured from the lower node id, so two edges in opposite directions
            # still bend to different sides.
            sign = 1 if endpoints(edge)[0] < endpoints(edge)[1] else -1
            bend = sign * (index - (len(group) - 1) / 2) * PARALLEL_EDGE_GAP
            parts.append(edge_part(start, end, bend, edge_label(edge)))
    return parts


def edge_part(start: Placed, end: Placed, bend: float, label: str) -> str:
    dx, dy = end.x - start.x, end.y - start.y
    length = (dx**2 + dy**2) ** 0.5
    ux, uy = dx / length, dy / length
    x1, y1 = start.x + ux * RADIUS, start.y + uy * RADIUS
    x2, y2 = end.x - ux * (RADIUS + 3), end.y - uy * (RADIUS + 3)
    # The control point sits beside the middle of the line. A curve passes halfway to it.
    cx, cy = (x1 + x2) / 2 - uy * bend * 2, (y1 + y2) / 2 + ux * bend * 2
    # The label sits past the middle, nearer to the end node. Edges that leave one node in a
    # fan are further apart there, so their labels do not cover each other.
    lx = x1 + (x2 - x1) * LABEL_POSITION - uy * bend
    ly = y1 + (y2 - y1) * LABEL_POSITION + ux * bend - 7
    return (
        f'<path d="M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}" fill="none"'
        f' stroke="{EDGE_COLOR}" stroke-width="1.4" marker-end="url(#arrow)"/>'
        f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" fill="{EDGE_COLOR}"'
        f' text-anchor="middle">{escape(label)}</text>'
    )


def edge_label(edge: Relationship) -> str:
    """Returns the type of an edge, with the payload and the source of a claim."""
    match edge.type:
        case "OWNS_STAKE_IN":
            return f"OWNS_STAKE_IN {edge['percentage']:g} % · {edge['source']} · {edge['as_of']}"
        case "SUBSIDIARY_OF":
            return f"SUBSIDIARY_OF · {edge['source']}"
        case _:
            return edge.type


def node_part(placed: Placed) -> str:
    label = next(iter(placed.node.labels))
    lines = wrapped(placed.title)
    first_line = placed.y - (len(lines) - 1) * 6.5 + 4
    title = "".join(
        f'<text x="{placed.x:.1f}" y="{first_line + index * 13:.1f}" font-size="11.5"'
        f' font-weight="600" fill="#1d1f23" text-anchor="middle">{escape(line)}</text>'
        for index, line in enumerate(lines)
    )
    return (
        f'<circle cx="{placed.x:.1f}" cy="{placed.y:.1f}" r="{RADIUS}"'
        f' fill="{NODE_COLORS[label]}" stroke="#1d1f23" stroke-opacity="0.25"/>'
        f"{title}"
        f'<text x="{placed.x:.1f}" y="{placed.y + RADIUS + 14:.1f}" font-size="10"'
        f' fill="{EDGE_COLOR}" text-anchor="middle">{escape(placed.detail)}</text>'
    )


def wrapped(title: str) -> list[str]:
    """Breaks a title into lines that fit inside a circle."""
    lines: list[str] = []
    for word in title.split():
        if lines and len(lines[-1]) + len(word) < 11:
            lines[-1] += f" {word}"
        else:
            lines.append(word)
    return lines


if __name__ == "__main__":
    main()

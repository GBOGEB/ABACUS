"""Minimal SVG/MathML inspection for lane-B tests.

Uses the stdlib HTML tokenizer rather than an XML parser, so the tests add no
untrusted-XML parsing surface. Tag and attribute names are lower-cased.
"""

from html.parser import HTMLParser


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = ""

    def get(self, name):
        return self.attrs.get(name.lower())

    def iter(self, tag=None):
        for child in self.children:
            if tag is None or child.tag == tag:
                yield child
            yield from child.iter(tag)

    def find_all(self, tag):
        return list(self.iter(tag))

    def find(self, tag):
        return next(self.iter(tag), None)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, attrs, self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.current = node.parent

    def handle_data(self, data):
        self.current.text += data


def parse(markup):
    """Return the single top-level element of ``markup``."""
    builder = _Builder()
    builder.feed(markup)
    builder.close()
    (top,) = builder.root.children
    return top

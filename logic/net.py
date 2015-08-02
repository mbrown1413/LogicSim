
from __future__ import division
import math

import numpy

import logic


class Net(object):

    def __init__(self, items):
        self._output = "float"

        self.nodes = []
        for i, item in enumerate(items):

            # Replace 1-terminal components with that terminal
            if isinstance(item, logic.Component):
                if len(item.terminals) != 1:
                    raise ValueError("Components can only be treated as "
                            "terminals if the component has only one terminal.")
                item = item.terminals.values()[0]

            if isinstance(item, NetNode):
                node = item
            else:
                neighbors = []
                if i != 0:
                    neighbors.append(i-1)
                if i < len(items) - 1:
                    neighbors.append(i+1)
                node = NetNode(item, neighbors)

                if isinstance(item, logic.components.Terminal):
                    item.connect(self)

            self.nodes.append(node)

        self.validate()

    @classmethod
    def from_json(cls, schematic):
        pass #TODO

    def draw(self, ctx, selected=False):

        lines_drawn = set()
        for i, node in enumerate(self.nodes):
            for j in node.neighbors:
                line = (min(i, j), max(i, j))
                if line not in lines_drawn:
                    ctx.move_to(*node.pos)
                    ctx.line_to(*self.nodes[j].pos)
                    lines_drawn.add(line)

        ctx.set_line_width(0.1)
        if selected:
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(*{
                "high": (0, 1, 0),
                "low": (0, 0, 0),
                "contention": (1, 0, 0),
                "float": (0.7, 0.7, 0.7),
            }[self._output])
        ctx.stroke()

        if selected:
            ctx.set_line_width(0.05)
            ctx.set_source_rgb(0, 0, 0)

            for term in self.terminals:
                ctx.save()
                term.component.transform(ctx)
                ctx.arc(term.pos[0], term.pos[1], 0.1, 0, math.pi*2)
                ctx.stroke()
                ctx.restore()

    def get_bbox(self):
        left = top = float('inf')
        right = bot = float('-inf')
        for node in self.nodes:
            left = min(left, node.pos[0])
            top = min(top, node.pos[1])
            right = max(right, node.pos[0])
            bot = max(bot, node.pos[1])
        return (left, top, right-left, bot-left)

    def update(self):

        def combine(terms):
            output = "float"
            states = [term.output for term in terms]
            for state in states:
                if state in ("high", "low"):
                    if output in ("high", "low") and state != output:
                        return "contention"
                    else:
                        output = state
                elif state == "contention":
                    return "contention"
            return output

        was_updated = False
        for term in self.terminals:
            # Consider the input to each terminal by looking at every terminal
            # but the one in question. This way no feedback effects can happen
            # where a terminal affects itself.
            others = set(self.terminals)
            others.remove(term)

            prev = term.input
            term.input = combine(others)
            if term.input != prev:
                was_updated = True

        self._output = combine(self.terminals)
        return was_updated

    def reset(self):
        self._output = "float"

    def validate(self):

        for node in self.nodes:
            assert node.terminal is None or node.terminal.net == self

        for i, node in enumerate(self.nodes):
            assert len(node.neighbors) >= 1
            for n in node.neighbors:
                # Nodes can't point to themselves
                assert i != n
                # When a node points to another node, that node must point back
                assert i in self.nodes[n].neighbors

        # No node should be isolated from the others
        visited = set()
        to_visit = set([0])
        while to_visit:
            n = to_visit.pop()
            visited.add(n)
            for neighbor in self.nodes[n].neighbors:
                if neighbor not in visited:
                    to_visit.add(neighbor)
        assert len(visited) == len(self.nodes)

    def remove(self, to_remove):
        if isinstance(to_remove, NetNode):
            idx = self.nodes.index(term)
        elif isinstance(to_remove, logic.components.Terminal):
            idx = [n.terminal for n in self.nodes].index(to_remove)
        else:  # Pos tuple
            idx = [n.pos for n in self.nodes].index(to_remove)
        self.nodes.pop(idx)

        # Rewrite neighbor indexes above `idx`
        for node in self.nodes:
            to_remove = []
            for i in range(len(node.neighbors)):
                if node.neighbors[i] == idx:
                    to_remove.append(i)
                elif node.neighbors[i] > idx:
                    node.neighbors[i] -= 1
            for r in to_remove[::-1]:
                node.neighbors.pop(r)

    @property
    def terminals(self):
        for node in self.nodes:
            term = node.terminal
            if term is not None:
                yield term

    def __str__(self):
        return "<Net {}>".format(' '.join([str(t)[1:-1] for t in self.terminals]))

    def point_intersect(self, point, line_thickness=0.3):
        point = numpy.array(point)

        closest_dist = float("inf")
        lines_visited = set()
        for i, node in enumerate(self.nodes):
            for j in node.neighbors:
                line = (min(i, j), max(i, j))
                if line not in lines_visited:
                    lines_visited.add(line)

                    node1 = self.nodes[i]
                    node2 = self.nodes[j]
                    dist = self._point_dist_to_segment(point, node1, node2)
                    if dist < closest_dist:
                        closest_dist = dist
                    if dist <= line_thickness / 2:
                        return True
        return False

    def _point_dist_to_segment(self, point, node1, node2):
        v1 = numpy.array(node2.pos) - numpy.array(node1.pos)
        v2 = point - numpy.array(node1.pos)

        # Project v2 onto v1
        v1_norm = numpy.linalg.norm(v1)
        v2_norm = numpy.linalg.norm(v2)
        v1_hat = v1 / v1_norm
        v2_hat = v2 / v2_norm
        proj = v1_hat.dot(v2) * v1_hat

        if proj.dot(v1) < 0 or numpy.linalg.norm(proj) > numpy.linalg.norm(v1):
            return float("inf")

        closest_point = node1.pos + proj
        return numpy.linalg.norm(closest_point - point)

class NetNode(object):

    def __init__(self, pos_or_terminal, neighbors):
        if isinstance(pos_or_terminal, logic.components.Terminal):
            self._pos = None
            self.terminal = pos_or_terminal
        else:
            assert len(pos_or_terminal) == 2
            self._pos = pos_or_terminal
            self.terminal = None

        self.neighbors = neighbors

    @property
    def pos(self):
        if self._pos is not None:
            return self._pos
        else:
            return self.terminal.component.transform_point(self.terminal.pos)

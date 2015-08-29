
from __future__ import division
from collections import OrderedDict
import math

import numpy

import logic
import _geometry


class Net(object):
    draggable = False

    def __init__(self, *items, **kwargs):
        self._scale = kwargs.pop("scale", None)
        if kwargs:
            raise ValueError("Unexpected keyword arguments: {}".format(kwargs))
        self._output = "float"

        self.nodes = []
        for i, item in enumerate(items):

            # Replace 1-terminal parts with that terminal
            if isinstance(item, logic.Part):
                if len(item.terminals) != 1:
                    raise ValueError("Parts can only be treated as "
                            "terminals if the part has only one terminal.")
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

                if isinstance(item, logic.Terminal):
                    item.connect(self)

            self.nodes.append(node)

        for term in self.terminals:
            term.net = self

        self.validate()

    def draw(self, ctx, selected=False, **kwargs):

        lines_drawn = set()
        for i, node in enumerate(self.nodes):
            for j in node.neighbors:
                line = (min(i, j), max(i, j))
                if line not in lines_drawn:
                    ctx.move_to(*node.pos)
                    ctx.line_to(*self.nodes[j].pos)
                    lines_drawn.add(line)

        ctx.set_line_width(0.1 * self.scale)
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
                term.part.transform(ctx)
                ctx.arc(term.pos[0], term.pos[1], 0.1, 0, math.pi*2)
                ctx.stroke()
                ctx.restore()

    @property
    def scale(self):
        if self._scale:
            return self._scale
        else:
            part_scales = map(lambda p: p.scale, self.parts)
            return max(part_scales) if part_scales else 1

    def get_bbox(self):
        left = top = float('inf')
        right = bot = float('-inf')
        for node in self.nodes:
            left = min(left, node.pos[0])
            top = min(top, node.pos[1])
            right = max(right, node.pos[0])
            bot = max(bot, node.pos[1])
        return (left, top, right-left, bot-top)

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
        if len(self.nodes) > 0:
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
        elif isinstance(to_remove, logic.Terminal):
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

    def connect(self, *items):
        node_items = [n.pos_or_terminal for n in self.nodes]

        connected_to_orig_nodes = False
        prev_node_idx = None
        for item in items:
            if item in node_items:
                connected_to_orig_nodes = True
                node_idx = node_items.index(item)
            else:
                node = NetNode(item, ())
                self.nodes.append(node)
                node_idx = len(self.nodes) - 1
            if prev_node_idx is not None:
                prev = self.nodes[prev_node_idx]
                prev.neighbors.append(node_idx)
                cur = self.nodes[node_idx]
                cur.neighbors.append(prev_node_idx)

            if isinstance(item, logic.Terminal):
                item.connect(self)

            prev_node_idx = node_idx

        # If these new connections don't connect to the original set of nodes,
        # we do that here.
        if not connected_to_orig_nodes:
            self.nodes[0].neighbors.append(len(self.nodes)-1)
            self.nodes[-1].append(0)

        self.validate()

    @property
    def terminals(self):
        for node in self.nodes:
            term = node.terminal
            if term is not None:
                yield term

    @property
    def parts(self):
        for term in self.terminals:
            yield term.part

    def __str__(self):
        return "<Net {}>".format(' '.join([str(t)[1:-1] for t in self.terminals]))

    def point_intersect(self, point, line_thickness=0.2):
        point = numpy.array(point)
        line_thickness *= self.scale

        closest_dist = float("inf")
        lines_visited = set()
        for i, node in enumerate(self.nodes):
            for j in node.neighbors:
                line = (min(i, j), max(i, j))
                if line not in lines_visited:
                    lines_visited.add(line)

                    node1 = self.nodes[i]
                    node2 = self.nodes[j]
                    dist = _geometry.line_distance_from_point(point, node1.pos, node2.pos)
                    if dist < closest_dist:
                        closest_dist = dist
                    if dist <= line_thickness / 2:
                        return True
        return False

    def get_dict(self):
        return {"nodes": [n.get_dict() for n in self.nodes]}

    @classmethod
    def combine(cls, net1, term1, net2, term2):
        assert term1 in net1.terminals
        assert term2 in net2.terminals
        result = Net()

        for node in net1.nodes:
            new_node = NetNode(node.pos_or_terminal, node.neighbors)
            result.nodes.append(new_node)
        for node in net2.nodes:
            new_neighbors = [n+len(net1.nodes) for n in node.neighbors]
            new_node = NetNode(node.pos_or_terminal, new_neighbors)
            result.nodes.append(new_node)

        for term in result.terminals:
            term.connect(result)
        result.connect(term1, term2)
        return result

class NetNode(object):

    def __init__(self, pos_or_terminal, neighbors):
        if isinstance(pos_or_terminal, logic.Terminal):
            self._pos = None
            self.terminal = pos_or_terminal
        else:
            assert len(pos_or_terminal) == 2
            self._pos = pos_or_terminal
            self.terminal = None

        self.neighbors = list(neighbors)

    @property
    def pos(self):
        if self._pos is not None:
            return self._pos
        else:
            return self.terminal.part.point_schematic_to_object(self.terminal.pos)

    @property
    def pos_or_terminal(self):
        if self._pos is not None:
            return self._pos
        else:
            return self.terminal

    def get_dict(self):
        if self._pos is not None:
            location = self._pos
        else:
            part = self.terminal.part
            if len(part.terminals) == 1:
                location = part.name
            else:
                location = "{}[{}]".format(part.name, self.terminal.name)

        return OrderedDict((
            ("location", location),
            ("neighbors", self.neighbors),
        ))

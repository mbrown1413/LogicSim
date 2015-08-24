
from __future__ import division
import collections
from copy import deepcopy
import json
import re

import numpy

import logic


# Matches "part[term]" or just "part"
term_re = re.compile(r"^([^[]+)(\[([^\]]+)\])?$")


class Schematic(object):
    """A collection of parts connected by nets."""

    def __init__(self, parts=(), nets=()):
        self.parts = set(parts)
        self.nets = set(nets)

    def draw(self, context, selected=(), **kwargs):
        default_draw_connections = kwargs.get('draw_terminals', False)

        for part in self.parts:
            if part in selected:
                kwargs['draw_terminals'] = True
            else:
                kwargs['draw_terminals'] = default_draw_connections

            context.save()
            part.draw(context, selected=part in selected, **kwargs)
            context.restore()

            """
            context.rectangle(*part.get_bbox())
            context.set_source_rgb(0, 1, 1)
            context.set_line_width(.2)
            context.stroke()
            """

        for net in self.nets:
            context.save()
            net.draw(context, selected=net in selected, **kwargs)
            context.restore()

    def add_part(self, part):
        assert isinstance(part, logic.Part)
        part.reset()
        self.parts.add(part)

    def add_parts(self, *parts):
        self.parts.update(parts)

    def remove(self, part):

        if isinstance(part, logic.Part):
            assert part in self.parts

            # Disconnect terminals from nets
            modified_nets = set()
            for term in part.terminals.itervalues():
                if term.net:
                    term.net.remove(term)
                    modified_nets.add(term.net)
                    term.net = None

            # Any nets that should be deleted?
            for net in modified_nets:
                if len(list(net.terminals)) < 2:
                    self.remove(net)

            self.parts.remove(part)

        elif isinstance(part, logic.Net):
            assert part in self.nets
            for term in part.terminals:
                term.net = None
                term.input = "float"

            self.nets.remove(part)

        self.update()

    def connect(self, *terms):
        net = None
        for i in range(1, len(terms)):
            net = self._connect2(terms[i], terms[i-1], net)

    def _connect2(self, term1, term2, net=None):

        def get_term_and_net(term):
            if isinstance(term, logic.Part):
                assert len(term.terminals) == 1
                term = term.terminals.values()[0]

            if isinstance(term, logic.Terminal):
                return term, term.net
            elif isinstance(term, tuple):
                return term, None
            else:
                assert False

        term1, net1 = get_term_and_net(term1)
        term2, net2 = get_term_and_net(term2)

        n_disconnected = [net1, net2].count(None)

        if n_disconnected == 2:
            if net is None:
                net = logic.Net(term1, term2)
                self.nets.add(net)
            else:
                 net.connect(term1, term2)
            return net
        elif n_disconnected == 1 or net1 == net2:
            if net1 == None:
                net1, net2 = net2, net1
            net1.connect(term1, term2)
            return net1
        elif n_disconnected == 0:
            self.nets.remove(net1)
            self.nets.remove(net2)
            new_net = logic.Net.combine(net1, term1, net2, term2)
            self.nets.add(new_net)
            return new_net

    def validate(self):

        all_terminals = set()
        for part in self.parts:
            assert isinstance(part, logic.Part)
            part.validate()

            for term in part.terminals.itervalues():
                assert term.net in self.nets or term.net is None

            all_terminals.update(part.terminals.values())

        for net in self.nets:
            assert isinstance(net, logic.Net)
            for term in net.terminals:
                assert term in all_terminals

    def reset(self):
        for part in self.parts:
            part.reset()
        for net in self.nets:
            net.reset()

    def update(self):

        to_visit = collections.deque(self.parts.union(self.nets))
        while to_visit:
            item = to_visit.popleft()

            if isinstance(item, logic.Net):
                was_updated = item.update()
                if was_updated:
                    to_visit.extend(set([term.part for term in item.terminals]))

            elif isinstance(item, logic.Part):
                prev_output = item.get_output_dict()
                item.update()
                cur_output = item.get_output_dict()
                for name, term in item.terminals.iteritems():
                    if prev_output[name] != cur_output[name]:
                        to_visit.append(term.net)

            elif item is not None:
                print item
                raise RuntimeError()

    def get_bbox(self):
        left = top = float('inf')
        right = bot = float('-inf')
        for item in list(self.parts) + list(self.nets):
            bbox  = item.get_bbox()
            x1, y1 = bbox[0], bbox[1]
            x2, y2 = bbox[0]+bbox[2], bbox[1]+bbox[3]
            left  = min(left,  x1, x2)
            top   = min(top,   y1, y2)
            right = max(right, x1, x2)
            bot   = max(bot,   y1, y2)
        return (left, top, right-left, bot-top)

    def part_at_pos(self, pos):
        for item in list(self.parts) + list(self.nets):
            if item.point_intersect(pos):
                return item
        return None

    def get_closest_terminal(self, pos, search_dist=float('inf')):
        pos = numpy.array(pos)

        closest_dist = float('inf')
        closest_term = None
        for part in self.parts:
            for term in part.terminals.itervalues():
                dist = numpy.linalg.norm(term.absolute_pos - pos)
                if dist <= closest_dist:
                    closest_dist = dist
                    closest_term = term
        if closest_dist > search_dist:
            return None
        else:
            return closest_term

    def get_part_by_name(self, name):
        #TODO: Optimize
        #TODO: Naming conflicts
        for part in self.parts:
            if part.name == name:
                return part
        return None

    @classmethod
    def from_json_str(cls, json_str):
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        data = deepcopy(data)
        s = cls()

        for desc in data.get('parts', ()):
            part_cls = logic.part_library[desc.pop('type')]
            part = part_cls(**desc)
            s.add_part(part)

        def node_from_dict(d):
            if isinstance(d['location'], list):
                loc = d['location']
            elif isinstance(d['location'], basestring):
                match = term_re.match(d['location'])
                part = s.get_part_by_name(match.group(1))
                assert part is not None
                if match.group(3):
                    loc = part[match.group(3)]
                else:
                    assert len(part.terminals) == 1
                    loc = part.terminals.values()[0]
            return logic.NetNode(loc, d['neighbors'])

        for desc in data.get('nets', ()):
            net = logic.Net(*map(node_from_dict, desc['nodes']))
            s.nets.add(net)

        return s

    @classmethod
    def from_file(cls, filename):
        text = open(filename, 'r').read()
        return cls.from_json_str(text)

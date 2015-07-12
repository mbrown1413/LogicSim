
from __future__ import division
import collections

import logic


class Schematic(object):
    """A collection of entities laid out onto a schematic."""

    def __init__(self):
        self.entities = set()
        self.nets = set()
        self.reset()

    def draw(self, context, selected=(), **kwargs):
        default_draw_connections = kwargs.get('draw_terminals', False)

        for entity in self.entities:
            context.save()
            if entity in selected:
                kwargs['draw_terminals'] = True
            else:
                kwargs['draw_terminals'] = default_draw_connections
            entity.draw(context, selected=entity in selected, **kwargs)
            context.restore()

            """
            context.rectangle(*entity.get_bbox())
            context.set_source_rgb(0, 1, 0)
            context.set_line_width(2)
            context.stroke()
            """

        for net in self.nets:
            context.save()
            net.draw(context)
            context.restore()

    def add_entity(self, entity):
        self.entities.add(entity)

    def add_entities(self, entities):
        self.entities.update(entities)

    def remove_entity(self, entity):
        self.entities.remove(entity)

    def connect(self, terminals):
        for term in terminals:
            if isinstance(term, logic.Component):
                # Single terminal component was given
                if len(term.terminals) != 1:
                    raise ValueError("Components can only be treated as terminals if the component has only one terminal.")
                term = term.terminals.values()[0]
            assert term.component in self.entities
            if term.net is not None:
                raise NotImplementedError()  #TODO

        new_net = logic.Net(terminals)
        self.nets.add(new_net)

    def validate(self):

        all_terminals = set()
        for entity in self.entities:
            entity.validate()

            if hasattr(entity, 'terminals'):
                for term in entity.terminals.itervalues():
                    assert term.net in self.nets or term.net is None

                all_terminals.update(entity.terminals.values())

        for net in self.nets:
            net.validate()

            for term in net.terminals:
                assert term in all_terminals

    def reset(self):
        self.n = -1
        for entity in self.entities:
            entity.reset()
        for net in self.nets:
            net.reset()

    def tick(self):
        self.n += 1
        for entity in self.entities:
            entity.tick()

        to_visit = collections.deque(list(self.entities) + list(self.nets))
        while to_visit:
            item = to_visit.popleft()

            if isinstance(item, logic.Net):
                was_updated = item.update()
                if was_updated:
                    to_visit.extend(set([term.component for term in item.terminals]))

            elif isinstance(item, logic.Component):
                prev_term_outs = item.get_output_dict()
                item.update()
                cur_term_outs = item.get_output_dict()
                for name, term in item.terminals.iteritems():
                    if prev_term_outs[name] != cur_term_outs[name]:
                        to_visit.append(term.net)

            else:
                print item
                raise RuntimeError()

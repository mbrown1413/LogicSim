
from __future__ import division
import math
import os

import cairo
import numpy

import logic


def rot_bbox_decorator(func):
    def wrap(self):
        result = func(self)
        if self.rot % 180 == 90:
            return (
                result[0] + result[2]/2 - result[3]/2,
                result[1] + result[3]/2 - result[2]/2,
                result[3], result[2]
            )
        elif self.rot % 180 == 0:
            return result
        else:
            raise NotImplementedError()
    return wrap


class Terminal(object):

    def __init__(self, component, name, pos, net=None, output="float"):
        self.component = component
        self.name = name
        self.pos = pos
        self.net = net
        self.output = output
        self.input = "float"

    def connect(self, net):
        self.disconnect()
        if net is None:
            return

        self.net = net
        net.terminals.add(self)

    def disconnect(self):
        if self.net:
            self.net.remove(self)
        self.net = None

    def reset(self):
        self.output = "float"
        self.input = "float"

    def __str__(self):
        if self.component.name:
            return "<{}[{}]>".format(self.component.name, self.name)
        else:
            return "<{}[{}]>".format(self.component, self.name)

    __repr__ = __str__


class Component(logic.Entity):

    def __init__(self, *args, **kwargs):
        super(Component, self).__init__(*args, **kwargs)
        self.terminals = {}

    def __getitem__(self, name):
        return self.terminals[name]

    def add_terminal(self, name, pos, net=None, output="float"):

        # Make unique name
        #TODO: No idea if this actually works
        orig_name = name
        i = 0
        i_str = ""
        while name in self.terminals:
            name = "{}{}".format(orig_name, i_str)
            i += 1
            i_str = str(i)

        t = Terminal(self, name, pos, output=output)
        self.terminals[name] = t
        return t

    def get_output_dict(self):
        return {name: term.output for name, term in self.terminals.iteritems()}

    def draw(self, ctx, **kwargs):
        if not kwargs.get('draw_terminals', False):
            return

        ctx.save()
        ctx.set_line_width(0.5/self.scale)
        ctx.set_source_rgb(0, 0, 0)
        self.transform(ctx)

        for term in self.terminals.itervalues():
            ctx.arc(term.pos[0], term.pos[1], 1/self.scale, 0, math.pi*2)
            ctx.stroke()

        ctx.restore()

    def validate(self):
        for term in self.terminals.itervalues():
            assert term.net is None or term in term.net.terminals

    def update(self):
        pass

    def tick(self):
        pass

    def reset(self):
        for term in self.terminals.itervalues():
            term.reset()


class TransistorEntity(Component):

    def __init__(self, *args, **kwargs):
        self.pmos = kwargs.pop("pmos", False)
        super(TransistorEntity, self).__init__(*args, **kwargs)
        self.scale = 5
        self.add_terminal("gate", (-2, 0))
        self.add_terminal("source", (2, -4))
        self.add_terminal("drain", (2, 4))

    @property
    def nmos(self):
        return not self.pmos

    def update(self):
        g, s, d = self["gate"], self["source"], self["drain"]
        g.output = "float"
        active = (self.nmos and g.input == "high") or \
                 (self.pmos and g.input == "low")

        if active:
            s.output, d.output = d.input, s.input

        elif g.input in ("contention", "float"):
            # s and d will output float when the transistor is active. They
            # will output s_out and d_out when inactive. If these two are
            # different, then output contention instead.
            s_out, d_out = d.input, s.input
            s.output = "contention" if s_out != "float" else "float"
            d.output = "contention" if d_out != "float" else "float"

        else:
            s.output = "float"
            d.output = "float"

    def draw(self, ctx, **kwargs):
        super(TransistorEntity, self).draw(ctx, **kwargs)

        self.transform(ctx)
        ctx.set_line_width(1.0/self.scale)
        if kwargs.get("selected", False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)

        if self.pmos:
            ctx.move_to(-2, 0)
            ctx.line_to(-0.55, 0)
            ctx.stroke()
            ctx.arc(-0.3, 0, 0.3, 0, 2*math.pi)
            ctx.stroke()
        else:
            ctx.move_to(-2, 0)
            ctx.line_to(0.2, 0)
            ctx.stroke()

        ctx.move_to(0.2, -1.5)
        ctx.line_to(0.2, 1.5)

        ctx.move_to(2, 4)
        ctx.line_to(2, 2)
        ctx.line_to(0.75, 2)
        ctx.line_to(0.75, -2)
        ctx.line_to(2, -2)
        ctx.line_to(2, -4)
        ctx.stroke()

    @rot_bbox_decorator
    def get_bbox(self):
        upper_left = self.pos - (self.scale*2, self.scale*4)
        return (
            upper_left[0], upper_left[1],
            self.scale*4, self.scale*8
        )


class SimpleTextComponent(Component):
    text = None  # Must be overwritten by subclass
    term_name = "term"
    term_pos = "bot"

    def __init__(self, *args, **kwargs):
        super(SimpleTextComponent, self).__init__(*args, **kwargs)
        if self.text is None:
            raise RuntimeError('Subclasses must overwrite "term" variable')
        pos = {"bot": (0, 0), "top": (0, -10)}[self.term_pos]
        self.add_terminal(self.term_name, pos)
        self.term = self.terminals[self.term_name]
        self.reset()

        # Get text dimmensiosn
        dummy_surface = cairo.SVGSurface(os.devnull, 0, 0)
        context = cairo.Context(dummy_surface)
        context.select_font_face("Courier")
        context.set_font_size(12)
        extents = context.text_extents(self.text)
        self.text_width = extents[2]
        self.text_height = extents[3]

    def draw(self, ctx, **kwargs):
        super(SimpleTextComponent, self).draw(ctx, **kwargs)
        self.transform(ctx)

        if kwargs.get("selected", False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.select_font_face("Courier")
        ctx.set_font_size(12)
        ctx.move_to(-self.text_width/2, 0)
        ctx.show_text(self.text)
        ctx.stroke()

    def get_bbox(self):
        #TODO: Broke when rotated
        return (self.pos[0]-self.text_width/2,
                self.pos[1]-self.text_height,
                self.text_width, self.text_height)


class VddComponent(SimpleTextComponent):
    text = "Vdd"
    term_name = "vdd"

    def validate(self):
        assert self['vdd'].output == "high"

    def reset(self):
        self['vdd'].output = "high"


class GndComponent(SimpleTextComponent):
    text = "Gnd"
    term_name = "gnd"
    term_pos = "top"

    def validate(self):
        assert self['gnd'].output == "low"

    def reset(self):
        self['gnd'].output = "low"


class ProbeComponent(Component):

    def __init__(self, *args, **kwargs):
        super(ProbeComponent, self).__init__(*args, **kwargs)
        self.add_terminal("term", (0, 0))
        self.r = 5

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        ctx.set_line_width(1.0/self.scale)

        # Outline
        ctx.arc(0, 0, self.r, 0, 2*math.pi)
        if kwargs.get("selected", False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.stroke()

        # Fill
        ctx.set_source_rgb(*{
            "high": (0, 1, 0),
            "low": (0, 0, 0),
            "contention": (1, 0, 0),
            "float": (1, 1, 1),
        }[self["term"].input])
        ctx.arc(0, 0, self.r, 0, 2*math.pi)
        ctx.fill()

    @rot_bbox_decorator
    def get_bbox(self):
        r = self.r + 1
        return (
            self.pos[0] - r,
            self.pos[1] - r,
            r*2, r*2
        )

    def point_intersect(self, point):
        return numpy.square(point - self.pos).sum() <= self.r**2


class SwitchComponent(Component):

    def __init__(self, *args, **kwargs):
        self.outputs = kwargs.pop('outputs', ("float", "high", "low", "contention"))
        super(SwitchComponent, self).__init__(*args, **kwargs)
        self.width = 5
        self.height = 10
        self.add_terminal("term", (0, 0), output=self.outputs[0])

    def on_activate(self):
        idx = self.outputs.index(self["term"].output)
        self["term"].output = self.outputs[(idx+1)%len(self.outputs)]

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        ctx.set_line_width(1.0/self.scale)

        # Fill
        ctx.set_source_rgb(*{
            "high": (0, 1, 0),
            "low": (0, 0, 0),
            "contention": (1, 0, 0),
            "float": (1, 1, 1),
        }[self["term"].output])
        ctx.rectangle(-self.width/2, -self.height/2, self.width, self.height)
        ctx.fill()

        # Outline
        ctx.rectangle(-self.width/2, -self.height/2, self.width, self.height)
        if kwargs.get("selected", False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.stroke()

    @rot_bbox_decorator
    def get_bbox(self):
        return (self.pos[0]-self.width/2, self.pos[1]-self.height/2,
                self.width, self.height)

    def reset(self):
        t = self['term']
        t.input = "float"
        t.output = self.outputs[0]


class IOComponent(Component):

    def __init__(self, *args, **kwargs):
        super(IOComponent, self).__init__(*args, **kwargs)
        self.add_terminal("term", (0, 0))

    def get_bbox(self):
        return (self.pos[0], self.pos[1], 0, 0)


class AggregateComponent(Component):

    def __init__(self, schematic, *args, **kwargs):
        super(AggregateComponent, self).__init__(*args, **kwargs)
        self.schematic = schematic

        self.terminal_pairs = []
        for entity in schematic.entities:
            if isinstance(entity, IOComponent):
                t = self.add_terminal(entity.name, entity.pos)
                self.terminal_pairs.append((t, entity["term"]))

    def draw(self, ctx, **kwargs):
        #TODO: Scale and such
        super(AggregateComponent, self).draw(ctx, **kwargs)

        self.transform(ctx)
        if kwargs.get('selected', False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.set_line_width(1.0/self.scale)

        bbox = self.get_bbox()
        ctx.rectangle(
            bbox[0]-self.pos[0],
            bbox[1]-self.pos[1],
            bbox[2],
            bbox[3],
        )

        ctx.stroke()

        del kwargs['selected']
        del kwargs['draw_terminals']
        self.schematic.draw(ctx, **kwargs)

    def get_bbox(self):
        bbox = self.schematic.get_bbox()
        return (
            bbox[0]+self.pos[0],
            bbox[1]+self.pos[1],
            bbox[2],
            bbox[3],
        )

    def validate(self):
        self.schematic.validate()

    def update(self):

        # Copy external inputs to IO Component outputs
        for external, internal in self.terminal_pairs:
            internal.output = external.input

        self.schematic.tick()

        # Copy IO Component inputs to external outputs
        for external, internal in self.terminal_pairs:
            external.output = internal.input

    def tick(self):
        for entity in self.schematic.entities:
            entity.tick()

    def reset(self):
        for item in list(self.schematic.entities) + list(self.schematic.nets):
            item.reset()

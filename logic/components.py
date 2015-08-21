
from __future__ import division
import math
import os

import cairo
import numpy

import logic


class Terminal(object):

    def __init__(self, component, name, pos, net=None, output="float"):
        self.component = component
        self.name = name
        self.pos = pos
        self.net = net
        self.output = output
        self.input = "float"

    def connect(self, net):
        if net is None:
            return

        self.net = net

    def reset(self):
        self.output = "float"
        self.input = "float"

    def point_intersect(self, point):
        dist = numpy.linalg.norm(point - self.absolute_pos)
        return dist <= 0.16

    @property
    def absolute_pos(self):
        return self.component.point_schematic_to_object(self.pos)

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
        ctx.set_line_width(0.05)
        ctx.set_source_rgb(0, 0, 0)
        self.transform(ctx)

        for term in self.terminals.itervalues():
            ctx.arc(term.pos[0], term.pos[1], 0.1, 0, math.pi*2)
            ctx.stroke()

        ctx.restore()

    def validate(self):
        for term in self.terminals.itervalues():
            assert term.net is None or term in term.net.terminals

    def update(self):
        pass

    def reset(self):
        for term in self.terminals.itervalues():
            term.reset()


class TransistorComponent(Component):

    def __init__(self, *args, **kwargs):
        self.pmos = kwargs.pop("pmos", False)
        super(TransistorComponent, self).__init__(*args, **kwargs)
        self.add_terminal("gate", (-1, 0))
        self.add_terminal("source", (1, -2))
        self.add_terminal("drain", (1, 2))

    @property
    def nmos(self):
        return not self.pmos

    def update(self):
        g, s, d = self["gate"], self["source"], self["drain"]
        g.output = "float"
        active = (self.nmos and g.input == "high") or \
                 (self.pmos and g.input == "low")

        if active:
            s.output = d.input
            d.output = s.input
        else:
            s.output = "float"
            d.output = "float"

    def draw(self, ctx, **kwargs):
        super(TransistorComponent, self).draw(ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        if self.pmos:
            ctx.move_to(-1, 0)
            ctx.line_to(-0.275, 0)
            ctx.stroke()
            ctx.arc(-0.15, 0, 0.15, 0, 2*math.pi)
            ctx.stroke()
        else:
            ctx.move_to(-1, 0)
            ctx.line_to(0.1, 0)
            ctx.stroke()

        ctx.move_to(0.1, -0.75)
        ctx.line_to(0.1, 0.75)

        ctx.move_to(1, 2)
        ctx.line_to(1, 1)
        ctx.line_to(0.375, 1)
        ctx.line_to(0.375, -1)
        ctx.line_to(1, -1)
        ctx.line_to(1, -2)
        ctx.stroke()

    def _get_bbox(self):
        return (
            -1, -2,
            2, 4
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
        #TODO: This class is unused, so not sure if this scale is realistic
        context.set_font_size(1)
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

    def _get_bbox(self):
        return (-self.text_width/2, -self.text_height,
                self.text_width, self.text_height)


class VddComponent(Component):

    def __init__(self, *args, **kwargs):
        super(VddComponent, self).__init__(*args, **kwargs)
        self.add_terminal("vdd", (0, 1))

    def reset(self):
        super(VddComponent, self).reset()
        self['vdd'].output = "high"

    def draw(self, ctx, **kwargs):
        super(VddComponent, self).draw(ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(0, -0.75)
        ctx.line_to(-0.5, 0)
        ctx.line_to(0.5, 0)
        ctx.line_to(0, -0.75)

        ctx.move_to(0, 0)
        ctx.line_to(0, 1)

        ctx.stroke()

    def _get_bbox(self):
        return (
            -0.5, -.75,
            1, 1.75
        )


class GndComponent(Component):

    def __init__(self, *args, **kwargs):
        super(GndComponent, self).__init__(*args, **kwargs)
        self.add_terminal("gnd", (0, -1))

    def reset(self):
        super(GndComponent, self).reset()
        self['gnd'].output = "low"

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(0, -1)
        ctx.line_to(0, 0)

        ctx.move_to(-.75, 0)
        ctx.line_to(.75, 0)

        ctx.move_to(-0.5, .25)
        ctx.line_to(0.5, .25)

        ctx.move_to(-0.25, 0.5)
        ctx.line_to(0.25, 0.5)

        ctx.stroke()
        super(GndComponent, self).draw(ctx, **kwargs)

    def _get_bbox(self):
        return (
            -.75, -1,
            1.5, 1.5
        )


class ProbeComponent(Component):

    def __init__(self, *args, **kwargs):
        super(ProbeComponent, self).__init__(*args, **kwargs)
        self.add_terminal("term", (0, 0))
        self.r = 0.4

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        # Outline
        ctx.arc(0, 0, self.r, 0, 2*math.pi)
        ctx.stroke()

        # Fill
        ctx.set_source_rgb(*{
            "high": (0, 1, 0),
            "low": (0, 0, 0),
            "contention": (1, 0, 0),
            "float": (1, 1, 1),
        }[self["term"].input])
        ctx.arc(0, 0, self.r-0.05, 0, 2*math.pi)
        ctx.fill()
        super(ProbeComponent, self).draw(ctx, **kwargs)

    def _get_bbox(self):
        r = self.r + 0.1
        return (
            -r, -r,
            r*2, r*2
        )

    def _point_intersect(self, point):
        return numpy.square(point).sum() <= self.r**2


class SwitchComponent(Component):

    def __init__(self, *args, **kwargs):
        self.outputs = kwargs.pop('outputs', ("float", "high", "low", "contention"))
        super(SwitchComponent, self).__init__(*args, **kwargs)
        self.width = 0.5
        self.height = 1
        self.add_terminal("term", (0, 0), output=self.outputs[0])

    def on_activate(self):
        idx = self.outputs.index(self["term"].output)
        self["term"].output = self.outputs[(idx+1)%len(self.outputs)]

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        ctx.set_line_width(0.1/self.scale)

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
        self.set_draw_settings(ctx, **kwargs)
        ctx.rectangle(-self.width/2, -self.height/2, self.width, self.height)
        ctx.stroke()

        super(SwitchComponent, self).draw(ctx, **kwargs)

    def _get_bbox(self):
        return (-self.width/2, -self.height/2,
                self.width, self.height)

    def reset(self):
        t = self['term']
        t.input = "float"
        t.output = self.outputs[0]


class IOComponent(Component):

    def __init__(self, *args, **kwargs):
        super(IOComponent, self).__init__(*args, **kwargs)
        self.add_terminal("term", (0, 0))

    def _get_bbox(self):
        return (0, 0, 0, 0)

    #TODO: Make this an actually drawn, editable component




######################################################
#TODO: Everything below will be removed in due time...
######################################################

class AggregateComponent(Component):
    io_positions = {}
    schematic_scale = None
    schematic_offset = (0, 0)

    def __init__(self, schematic, *args, **kwargs):
        super(AggregateComponent, self).__init__(*args, **kwargs)
        self.schematic = schematic

        self.terminal_pairs = []
        for entity in schematic.entities:
            if isinstance(entity, IOComponent):
                pos = self.io_positions.get(entity.name, entity.pos)
                t = self.add_terminal(entity.name, pos)
                self.terminal_pairs.append((t, entity["term"]))

        self.schematic.reset()

    def draw(self, ctx, **kwargs):
        super(AggregateComponent, self).draw(ctx, **kwargs)
        del kwargs['selected']
        del kwargs['draw_terminals']

        if self.schematic_scale:
            scale = self.schematic_scale
        else:
            bbox1 = self.schematic.get_bbox()
            bbox2 = self.get_bbox()
            scale = min(bbox2[2]/bbox1[2], bbox2[3]/bbox1[3])

        ctx.save()
        self.transform(ctx)
        ctx.translate(*self.schematic_offset)
        ctx.scale(scale, scale)
        self.schematic.draw(ctx)
        ctx.restore()

        ctx.save()
        self.transform(ctx)

        ctx.restore()

    def _get_bbox(self):
        return self.schematic.get_bbox()

    def validate(self):
        self.schematic.validate()

    def update(self):

        # Copy external inputs to IO Component outputs
        for external, internal in self.terminal_pairs:
            internal.output = external.input

        self.schematic.update()

        # Copy IO Component inputs to external outputs
        for external, internal in self.terminal_pairs:
            external.output = internal.input

    def reset(self):
        self.schematic.reset()
        super(AggregateComponent, self).reset()


class NotGateComponent(AggregateComponent):
    io_positions = {
        "in": (-2, 0),
        "out": (2, 0),
    }
    schematic_scale = 0.12
    schematic_offset = (-.7, 0)

    def __init__(self, *args, **kwargs):
        vdd = VddComponent((1, -5))
        gnd = GndComponent((1, 5))
        io_in = IOComponent((-2, 0), name="in")
        t1 = TransistorComponent((0, 2), name="t1")
        t2 = TransistorComponent((0, -2), name="t2", pmos=True)
        io_out = IOComponent((15, 0), name="out")
        schematic = logic.Schematic()
        schematic.add_entities((
            vdd, gnd, io_in, t1, t2, io_out
        ))
        schematic.connect(vdd, t2['source'])
        schematic.connect(gnd, t1['drain'])
        schematic.connect(t1['gate'], io_in, t2['gate'])
        schematic.connect(io_out, t1['source'], t2['drain'])

        super(NotGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        super(NotGateComponent, self).draw(ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, 0)
        ctx.line_to(-1, 0)

        ctx.move_to(-1, -1)
        ctx.line_to(-1, 1)
        ctx.line_to(1, 0)
        ctx.line_to(-1, -1)
        ctx.stroke()

        ctx.arc(1.25, 0, 0.15, 0, 2*math.pi)
        ctx.stroke()

        ctx.move_to(1.4, 0)
        ctx.line_to(2, 0)
        ctx.stroke()

    def _get_bbox(self):
        return (
            -2, -1,
            4, 2
        )


class NorGateComponent(AggregateComponent):
    io_positions = {
        "in1": (-3, -1),
        "in2": (-3, 1),
        "out": (3, 0),
    }
    schematic_scale = 0.2
    schematic_offset = (-.2, .5)

    def __init__(self, *args, **kwargs):
        vdd = VddComponent((0, -11))
        gnd = GndComponent((0, 5))
        io_in1 = IOComponent((-8, -5), name="in1")
        io_in2 = IOComponent((-8, 5), name="in2")
        io_out = IOComponent((8, 0), name="out")
        t1 = TransistorComponent((-1, -7), pmos=True)
        t2 = TransistorComponent((-1, -2), pmos=True)
        t3 = TransistorComponent((-4, 2))
        t4 = TransistorComponent((2, 2))

        schematic = logic.Schematic()
        schematic.add_entities((
            vdd, gnd, io_in1, io_in2, io_out, t1, t2, t3, t4
        ))
        schematic.connect(io_in1, t1['gate'], t3['gate'])
        schematic.connect(io_in2, t2['gate'], t4['gate'])
        schematic.connect(vdd, t1['source'])
        schematic.connect(t1['drain'], t2['source'])
        schematic.connect(gnd, t3['drain'], t4['drain'])
        schematic.connect(t2['drain'], t3['source'], t4['source'], io_out)

        super(NorGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        super(NorGateComponent, self).draw(ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, -2)
        ctx.curve_to(-1, -.5, -1, 0.5, -2, 2)
        ctx.line_to(-1, 2)
        ctx.curve_to(0, 2, 1.5, 1, 2, 0)
        ctx.curve_to(1.5, -1, 0, -2, -1, -2)
        ctx.line_to(-2, -2)

        ctx.move_to(-3, -1)
        ctx.line_to(-1.45, -1)

        ctx.move_to(-3, 1)
        ctx.line_to(-1.45, 1)

        ctx.move_to(2.4, 0)
        ctx.line_to(3, 0)

        ctx.stroke()

        ctx.arc(2.25, 0, 0.15, 0, 2*math.pi)
        ctx.stroke()

    def _get_bbox(self):
        return (
            -3, -2,
            6, 4
        )


class NandGateComponent(AggregateComponent):
    io_positions = {
        "in1": (-3, -1),
        "in2": (-3, 1),
        "out": (3, 0),
    }

    def __init__(self, *args, **kwargs):
        vdd = VddComponent((0, -5))
        gnd = GndComponent((0, 5))
        io_in1 = IOComponent((-3, 0), name="in1")
        io_in2 = IOComponent((-3, 5), name="in2")
        io_out = IOComponent((10, 0), name="out")
        t1 = TransistorComponent((0, 0), pmos=True)
        t2 = TransistorComponent((5, 0), pmos=True)
        t3 = TransistorComponent((0, 5))
        t4 = TransistorComponent((5, 5))

        schematic = logic.Schematic()
        schematic.add_entities((
            vdd, gnd, io_in1, io_in2, io_out, t1, t2, t3, t4
        ))
        schematic.connect(io_in1, t1['gate'], t3['gate'])
        schematic.connect(io_in2, t2['gate'], t4['gate'])
        schematic.connect(vdd, t1['source'], t2['source'])
        schematic.connect(gnd, t3['source'])
        schematic.connect(t3['drain'], t4['source'])
        schematic.connect(io_out, t1['drain'], t2['drain'], t4['drain'])

        super(NandGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        AggregateComponent.draw(self, ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, -2)
        ctx.line_to(-2, 2)
        ctx.line_to(-1, 2)
        ctx.curve_to(0, 2, 2, 2, 2, 0)
        ctx.curve_to(2, -2, 0, -2, -1, -2)
        ctx.line_to(-2, -2)

        ctx.move_to(-3, 1)
        ctx.line_to(-2, 1)

        ctx.move_to(-3, -1)
        ctx.line_to(-2, -1)

        ctx.move_to(2.4, 0)
        ctx.line_to(3, 0)

        ctx.stroke()

        ctx.arc(2.25, 0, 0.15, 0, 2*math.pi)
        ctx.stroke()


    def _get_bbox(self):
        return (
            -3, -2,
            6, 4
        )


class AndGateComponent(AggregateComponent):
    io_positions = {
        "in1": (-3, -1),
        "in2": (-3, 1),
        "out": (3, 0),
    }

    def __init__(self, *args, **kwargs):
        gate_nand = NandGateComponent()
        gate_not = NotGateComponent()
        io_in1 = IOComponent(name="in1")
        io_in2 = IOComponent(name="in2")
        io_out = IOComponent(name="out")

        schematic = logic.Schematic()
        schematic.add_entities((
            gate_nand, gate_not, io_in1, io_in2, io_out
        ))
        schematic.connect(gate_nand["in1"], io_in1)
        schematic.connect(gate_nand["in2"], io_in2)
        schematic.connect(gate_nand["out"], gate_not["in"])
        schematic.connect(gate_not["out"], io_out)

        super(AndGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        Component.draw(self, ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, -2)
        ctx.line_to(-2, 2)
        ctx.line_to(-1, 2)
        ctx.curve_to(0, 2, 2, 2, 2, 0)
        ctx.curve_to(2, -2, 0, -2, -1, -2)
        ctx.line_to(-2, -2)

        ctx.move_to(-3, 1)
        ctx.line_to(-2, 1)

        ctx.move_to(-3, -1)
        ctx.line_to(-2, -1)

        ctx.move_to(2, 0)
        ctx.line_to(3, 0)

        ctx.stroke()


class OrGateComponent(AggregateComponent):
    io_positions = {
        "in1": (-3, -1),
        "in2": (-3, 1),
        "out": (3, 0),
    }

    def __init__(self, *args, **kwargs):
        gate_nor = NorGateComponent()
        gate_not = NotGateComponent()
        io_in1 = IOComponent(name="in1")
        io_in2 = IOComponent(name="in2")
        io_out = IOComponent(name="out")

        schematic = logic.Schematic()
        schematic.add_entities((
            gate_nor, gate_not, io_in1, io_in2, io_out
        ))
        schematic.connect(gate_nor["in1"], io_in1)
        schematic.connect(gate_nor["in2"], io_in2)
        schematic.connect(gate_nor["out"], gate_not["in"])
        schematic.connect(gate_not["out"], io_out)

        super(OrGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        Component.draw(self, ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, -2)
        ctx.curve_to(-1, -0.5, -1, 0.5, -2, 2)
        ctx.line_to(-1, 2)
        ctx.curve_to(0, 2, 1.5, 1, 2, 0)
        ctx.curve_to(1.5, -1, 0, -2, -1, -2)
        ctx.line_to(-2, -2)

        ctx.move_to(-3, -1)
        ctx.line_to(-1.45, -1)

        ctx.move_to(-3, 1)
        ctx.line_to(-1.45, 1)

        ctx.move_to(2, 0)
        ctx.line_to(3, 0)

        ctx.stroke()

    def _get_bbox(self):
        return (
            -3, -2,
            6, 4
        )


class XorGateComponent(AggregateComponent):
    io_positions = {
        "in1": (-3, -1),
        "in2": (-3, 1),
        "out": (3, 0),
    }

    def __init__(self, *args, **kwargs):
        vdd = VddComponent((-5, -10))
        gnd = GndComponent((-5, 10))
        not1 = NotGateComponent((-10, -5))
        not2 = NotGateComponent((-10, 5))
        in1 = IOComponent((-15, -5), name="in1")
        in2 = IOComponent((-15, 5), name="in2")
        out = IOComponent((10, 0), name="out")
        t1 = TransistorComponent((0, -7.5), pmos=True)
        t2 = TransistorComponent((0, -2.5), pmos=True)
        t3 = TransistorComponent((5, -7.5), pmos=True)
        t4 = TransistorComponent((5, -2.5), pmos=True)
        t5 = TransistorComponent((0, 7.5))
        t6 = TransistorComponent((0, 2.5))
        t7 = TransistorComponent((5, 7.5))
        t8 = TransistorComponent((5, 2.5))

        schematic = logic.Schematic()
        schematic.add_entities((
            vdd, gnd, not1, not2, in1, in2, out, t1, t2, t3, t4, t5, t6, t7, t8
        ))
        schematic.connect(vdd, t1['source'], t3['source'])
        schematic.connect(t1['drain'], t2['source'])
        schematic.connect(t3['drain'], t4['source'])
        schematic.connect(gnd, t6['drain'], t8['drain'])
        schematic.connect(t5['drain'], t6['source'])
        schematic.connect(t7['drain'], t8['source'])
        schematic.connect(out, t2['drain'], t4['drain'], t5['source'], t7['source'])

        schematic.connect(in1, not1['in'], t1['gate'], t5['gate'])
        schematic.connect(in2, not2['in'], t4['gate'], t6['gate'])
        schematic.connect(not1['out'], t3['gate'], t7['gate'])
        schematic.connect(not2['out'], t2['gate'], t8['gate'])

        super(XorGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        Component.draw(self, ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, -2)
        ctx.curve_to(-1, -0.5, -1, 0.5, -2, 2)
        ctx.line_to(-1, 2)
        ctx.curve_to(0, 2, 1.5, 1, 2, 0)
        ctx.curve_to(1.5, -1, 0, -2, -1, -2)
        ctx.line_to(-2, -2)

        ctx.move_to(-3, -1)
        ctx.line_to(-1.45, -1)

        ctx.move_to(-3, 1)
        ctx.line_to(-1.45, 1)

        ctx.move_to(2, 0)
        ctx.line_to(3, 0)

        ctx.move_to(-2.5, -2)
        ctx.curve_to(-1.5, -0.5, -1.5, 0.5, -2.5, 2)

        ctx.stroke()

    def _get_bbox(self):
        return (
            -3, -2,
            6, 4
        )


class XnorGateComponent(AggregateComponent):
    io_positions = {
        "in1": (-3, -1),
        "in2": (-3, 1),
        "out": (3, 0),
    }

    def __init__(self, *args, **kwargs):
        vdd = VddComponent((-5, -10))
        gnd = GndComponent((-5, 10))
        not1 = NotGateComponent((-10, -5))
        not2 = NotGateComponent((-10, 5))
        in1 = IOComponent((-15, -5), name="in1")
        in2 = IOComponent((-15, 5), name="in2")
        out = IOComponent((10, 0), name="out")
        t1 = TransistorComponent((0, -7.5), pmos=True)
        t2 = TransistorComponent((0, -2.5), pmos=True)
        t3 = TransistorComponent((5, -7.5), pmos=True)
        t4 = TransistorComponent((5, -2.5), pmos=True)
        t5 = TransistorComponent((0, 7.5))
        t6 = TransistorComponent((0, 2.5))
        t7 = TransistorComponent((5, 7.5))
        t8 = TransistorComponent((5, 2.5))

        schematic = logic.Schematic()
        schematic.add_entities((
            vdd, gnd, not1, not2, in1, in2, out, t1, t2, t3, t4, t5, t6, t7, t8
        ))
        schematic.connect(vdd, t1['source'], t3['source'])
        schematic.connect(t1['drain'], t2['source'])
        schematic.connect(t3['drain'], t4['source'])
        schematic.connect(gnd, t6['drain'], t8['drain'])
        schematic.connect(t5['drain'], t6['source'])
        schematic.connect(t7['drain'], t8['source'])
        schematic.connect(out, t2['drain'], t4['drain'], t5['source'], t7['source'])

        schematic.connect(in1, not1['in'], t1['gate'], t5['gate'])
        schematic.connect(in2, not2['in'], t2['gate'], t8['gate'])
        schematic.connect(not1['out'], t3['gate'], t7['gate'])
        schematic.connect(not2['out'], t4['gate'], t6['gate'])

        super(XnorGateComponent, self).__init__(schematic, *args, **kwargs)

    def draw(self, ctx, **kwargs):
        AggregateComponent.draw(self, ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(-2, -2)
        ctx.curve_to(-1, -0.5, -1, 0.5, -2, 2)
        ctx.line_to(-1, 2)
        ctx.curve_to(0, 2, 1.5, 1, 2, 0)
        ctx.curve_to(1.5, -1, 0, -2, -1, -2)
        ctx.line_to(-2, -2)

        ctx.move_to(-3, -1)
        ctx.line_to(-1.45, -1)

        ctx.move_to(-3, 1)
        ctx.line_to(-1.45, 1)

        ctx.move_to(2.4, 0)
        ctx.line_to(3, 0)

        ctx.move_to(-2.5, -2)
        ctx.curve_to(-1.5, -0.5, -1.5, 0.5, -2.5, 2)

        ctx.stroke()

        ctx.arc(2.25, 0, 0.15, 0, 2*math.pi)
        ctx.stroke()

    def _get_bbox(self):
        return (
            -3, -2,
            6, 4
        )

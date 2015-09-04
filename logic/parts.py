

from __future__ import division
from collections import OrderedDict
import math
import os

import numpy
import cairo

import logic
import _geometry


class Part(object):
    draggable = True
    saved_fields = ("part_type", "name", "pos", "scale", "rot", "line_width")
    part_type = None  # Must be overwriten by subclasses

    def __init__(self, pos=(0, 0), scale=1, rot=0, name=None, line_width=0.1):
        self.pos = numpy.array(pos)
        self.scale = scale
        self.rot = rot
        self.name = name
        self.line_width = line_width
        self.terminals = {}
        self.parent_schematic = None

        assert self.part_type is not None

    def _register_schematic(self, schematic):
        self.parent_schematic = schematic

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

        t = logic.Terminal(self, name, pos, output=output)
        self.terminals[name] = t
        return t

    def get_output_dict(self):
        return {name: term.output for name, term in self.terminals.iteritems()}

    def transform(self, context):
        context.translate(*self.pos)
        context.scale(self.scale, self.scale)
        context.rotate(math.radians(self.rot))

    def point_schematic_to_object(self, point, _reverse=False):
        """Converts `point` from schematic to object space."""
        dummy_surface = cairo.SVGSurface(os.devnull, 0, 0)
        ctx = cairo.Context(dummy_surface)
        ctx.identity_matrix()
        self.transform(ctx)
        if _reverse:
            return ctx.device_to_user(*point)
        else:
            return ctx.user_to_device(*point)

    def point_object_to_schematic(self, point):
        """Converts `point` from object to schematic space."""
        return self.point_schematic_to_object(point, _reverse=True)

    def rect_object_to_schematic(self, rect):
        """Converts `rect` from object to schematic space."""

        # Get 4 points of the rectangle
        point1 = (rect[0],         rect[1]        )
        point2 = (rect[0]+rect[2], rect[1]        )
        point3 = (rect[0]+rect[2], rect[1]+rect[3])
        point4 = (rect[0],         rect[1]+rect[3])
        points = (point1, point2, point3, point4)

        # Transform points to schematic space, then get their bounding box
        points = map(self.point_schematic_to_object, points)
        xs = map(lambda p: p[0], points)
        ys = map(lambda p: p[1], points)
        return (
            min(xs),
            min(ys),
            max(xs) - min(xs),
            max(ys) - min(ys),
        )

    def set_draw_settings(self, ctx, **kwargs):
        self.set_color(ctx, **kwargs)
        self.set_line_width(ctx, **kwargs)

    def set_color(self, ctx, **kwargs):
        if kwargs.get('selected', False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)

    def set_line_width(self, ctx, **kwargs):
        ctx.set_line_width(self.line_width)

    def get_bbox(self):
        """Gets bounding box in schematic space.

        Returns: (x, y, width, height)
            Where (x, y) is the top left of the rectangle.

        """
        return self.rect_object_to_schematic(self._get_bbox())

    def _get_bbox(self):
        """Like `get_bbox()`, but returns the bbox in object space."""
        raise NotImplementedError()

    def point_intersect(self, point):
        """Returns `True` if `point` is inside the part."""
        return self._point_intersect(self.point_object_to_schematic(point))

    def _point_intersect(self, point):
        """Like `point_intersect()`, but accepts `point` in object space."""
        bbox = self._get_bbox()
        left, top = bbox[0], bbox[1]
        right = left + bbox[2]
        bottom = top + bbox[3]
        return point[0] >= left and point[1] >= top and \
               point[0] <= right and point[1] <= bottom

    def rotate(self, degrees):
        self.rot = (self.rot + degrees) % 360

    def get_dict(self):

        cls_hierarchy = []
        to_visit = [self.__class__]
        while to_visit:
            cls = to_visit.pop()
            if issubclass(cls, Part):
                cls_hierarchy.append(cls)
                to_visit.extend(cls.__bases__)

        fields = []
        for cls in cls_hierarchy[::-1]:
            fields.extend(getattr(cls, "saved_fields", ()))

        d = OrderedDict()
        for field in fields:
            value = getattr(self, field)
            if isinstance(value, numpy.ndarray):
                value = list(value)
            d[field] = value
        return d

    def __str__(self):
        name_str = ""
        if self.name:
            name_str = ' "{}"'.format(self.name)
        return "<{}{}>".format(self.__class__.__name__, name_str)

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

    def on_activate(self):
        pass

    def update(self):
        pass

    def reset(self):
        for term in self.terminals.itervalues():
            term.reset()


class DrawingPart(Part):

    def __init__(self, *args, **kwargs):
        self.color = kwargs.pop("color", (0, 0, 0))
        super(DrawingPart, self).__init__(*args, **kwargs)

    def set_color(self, ctx, **kwargs):
        if kwargs.get('selected', False):
            ctx.set_source_rgb(0, 0, 1)
        elif isinstance(self.color, (tuple, list)):
            ctx.set_source_rgb(*self.color)
        elif isinstance(self.color, basestring):
            term = self.parent_schematic.get_terminal_by_name(self.color)
            ctx.set_source_rgb(*term.color)
        else:
            assert False


class LinesPart(DrawingPart):
    part_type = "Lines"
    saved_fields = ("points",)

    def __init__(self, *args, **kwargs):
        self.points = kwargs.pop('points')
        super(LinesPart, self).__init__(*args, **kwargs)

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.move_to(*self.points[0])
        for point in self.points[1:]:
            ctx.line_to(*point)
        ctx.stroke()

    def _get_bbox(self):
        xs = map(lambda p: p[0], self.points)
        ys = map(lambda p: p[1], self.points)
        return (
            min(xs), min(ys),
            max(xs)-min(xs), max(ys)-min(ys)
        )

    def _point_intersect(self, point):
        point = numpy.array(point)

        for p1, p2 in self.lines:
            dist = _geometry.line_distance_from_point(point, p1, p2)
            if dist < self.line_width / 2:
                return True
        return False

    @property
    def lines(self):
        for i in range(1, len(self.points)):
            yield (self.points[i-1], self.points[i])


class CirclePart(DrawingPart):
    part_type = "Circle"
    saved_fields = ("radius",)

    def __init__(self, *args, **kwargs):
        self.radius = kwargs.pop('radius')
        super(CirclePart, self).__init__(*args, **kwargs)

    def draw(self, ctx, **kwargs):
        super(CirclePart, self).draw(ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.arc(0, 0, self.radius, 0, math.pi*2)
        ctx.stroke()

    def _get_bbox(self):
        l = self.radius + self.line_width
        return (
            -l, -l,
            l*2, l*2
        )


class TransistorPart(Part):
    part_type = "Transistor"
    saved_fields = ("pmos",)

    def __init__(self, *args, **kwargs):
        self.pmos = kwargs.pop("pmos", False)
        super(TransistorPart, self).__init__(*args, **kwargs)
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
        super(TransistorPart, self).draw(ctx, **kwargs)
        if kwargs.get("selected", False):
            gate_color = src_color = drain_color = black_color = (0, 0, 1)
        else:
            gate_color = self["gate"].color
            src_color = self["source"].color
            drain_color = self["drain"].color
            black_color = (0, 0, 0)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.set_source_rgb(*black_color)
        if self.pmos:
            ctx.arc(-0.15, 0, 0.15, 0, 2*math.pi)
            ctx.stroke()
            ctx.set_source_rgb(*gate_color)
            ctx.move_to(-1, 0)
            ctx.line_to(-0.275, 0)
            ctx.stroke()
        else:
            ctx.set_source_rgb(*gate_color)
            ctx.move_to(-1, 0)
            ctx.line_to(0.1, 0)
            ctx.stroke()

        ctx.set_source_rgb(*black_color)
        ctx.move_to(0.1, -0.75)
        ctx.line_to(0.1, 0.75)
        ctx.move_to(0.375, 1)
        ctx.line_to(0.375, -1)
        ctx.stroke()

        ctx.set_source_rgb(*drain_color)
        ctx.move_to(1, 2)
        ctx.line_to(1, 1)
        ctx.line_to(0.375, 1)
        ctx.stroke()

        ctx.set_source_rgb(*src_color)
        ctx.move_to(0.375, -1)
        ctx.line_to(1, -1)
        ctx.line_to(1, -2)
        ctx.stroke()

    def _get_bbox(self):
        return (
            -1, -2,
            2, 4
        )


class VddPart(Part):
    part_type = "Vdd"

    def __init__(self, *args, **kwargs):
        super(VddPart, self).__init__(*args, **kwargs)
        self.add_terminal("vdd", (0, 1))

    def reset(self):
        super(VddPart, self).reset()
        self['vdd'].output = "high"

    def draw(self, ctx, **kwargs):
        super(VddPart, self).draw(ctx, **kwargs)

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


class GndPart(Part):
    part_type = "Gnd"

    def __init__(self, *args, **kwargs):
        super(GndPart, self).__init__(*args, **kwargs)
        self.add_terminal("gnd", (0, -1))

    def reset(self):
        super(GndPart, self).reset()
        self['gnd'].output = "low"

    def draw(self, ctx, **kwargs):
        super(GndPart, self).draw(ctx, **kwargs)
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

    def _get_bbox(self):
        return (
            -.75, -1,
            1.5, 1.5
        )


class ProbePart(Part):
    part_type = "Probe"

    def __init__(self, *args, **kwargs):
        super(ProbePart, self).__init__(*args, **kwargs)
        self.add_terminal("term", (0, 0))
        self.r = 0.4

    def draw(self, ctx, **kwargs):
        ctx.save()
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

        ctx.restore()
        super(ProbePart, self).draw(ctx, **kwargs)

    def _get_bbox(self):
        r = self.r + 0.1
        return (
            -r, -r,
            r*2, r*2
        )

    def _point_intersect(self, point):
        return numpy.square(point).sum() <= self.r**2


class SwitchPart(Part):
    part_type = "Switch"
    saved_fields = ("outputs",)

    def __init__(self, *args, **kwargs):
        self.outputs = kwargs.pop('outputs', ("float", "high", "low", "contention"))
        super(SwitchPart, self).__init__(*args, **kwargs)
        self.width = 0.5
        self.height = 1
        self.add_terminal("term", (0, 0), output=self.outputs[0])

    def on_activate(self):
        idx = self.outputs.index(self["term"].output)
        self["term"].output = self.outputs[(idx+1)%len(self.outputs)]

    def draw(self, ctx, **kwargs):
        ctx.save()
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

        ctx.restore()
        super(SwitchPart, self).draw(ctx, **kwargs)

    def _get_bbox(self):
        return (-self.width/2, -self.height/2,
                self.width, self.height)

    def reset(self):
        t = self['term']
        t.input = "float"
        t.output = self.outputs[0]


class IOPart(Part):
    part_type = "IO"

    def __init__(self, *args, **kwargs):
        super(IOPart, self).__init__(*args, **kwargs)
        self.add_terminal("term", (0, 0))
        self.r = 0.4

    def _get_bbox(self):
        r = self.r + 0.1
        return (
            -r, -r,
            r*2, r*2
        )

    def _point_intersect(self, point):
        return numpy.square(point).sum() <= self.r**2

    def draw(self, ctx, **kwargs):
        ctx.save()

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)
        ctx.set_source_rgb(1, 0, 1)
        ctx.arc(0, 0, self.r, 0, 2*math.pi)
        ctx.fill()

        ctx.restore()
        super(IOPart, self).draw(ctx, **kwargs)


class AggregatePart(Part):

    def __init__(self, schematic, part_type, *args, **kwargs):
        self.schematic = schematic
        self.schematic.reset()
        self.part_type = part_type

        super(AggregatePart, self).__init__(*args, **kwargs)

        # Pairs terminals, connecting the terminals from the aggregate part to
        # the IO part terminals of the underlying schematic.
        self.terminal_pairs = []
        for part in schematic.parts:
            if isinstance(part, IOPart):
                t = self.add_terminal(part.name, part.pos)
                self.terminal_pairs.append((t, part['term']))

    def draw(self, ctx, **kwargs):
        super(AggregatePart, self).draw(ctx, **kwargs)
        del kwargs['draw_terminals']
        if kwargs.get('selected', False):
            kwargs['selected'] = filter(lambda p: isinstance(p, DrawingPart), self.schematic.parts)
        else:
            kwargs['selected'] = ()

        self.transform(ctx)
        self.schematic.draw(ctx, draw_io_parts=False, **kwargs)

    def update(self):

        # Copy external inputs to IO Component outputs
        for external, internal in self.terminal_pairs:
            internal.output = external.input

        self.schematic.update()

        # Copy IO Component inputs to external outputs
        for external, internal in self.terminal_pairs:
            external.output = internal.input

    def _get_bbox(self):
        return self.schematic.get_bbox()

    def reset(self):
        self.schematic.reset()
        super(AggregatePart, self).reset()

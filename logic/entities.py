
from __future__ import division
import math
import os

import numpy
import cairo


class Entity(object):
    draggable = True

    def __init__(self, pos=(0, 0), scale=1, rot=0, name=None, line_width=0.1):
        self.pos = numpy.array(pos)
        self.scale = scale
        self.rot = rot
        self.name = name
        self.line_width = line_width
        self.terminals = {}

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
        if kwargs.get('selected', False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
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
        """Returns `True` if `point` is inside the entity."""
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

    def __str__(self):
        name_str = ""
        if self.name:
            name_str = ' "{}"'.format(self.name)
        return "<{}{}>".format(self.__class__.__name__, name_str)

    def get_json_dict(self):
        raise NotImplementedError()  #TODO

    def get_output_dict(self):
        return None

    def draw(self, context, **kwargs):
        pass

    def validate(self):
        pass

    def on_activate(self):
        pass

    def update(self):
        pass

    def reset(self):
        pass

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class LinesEntity(Entity):

    def __init__(self, *args, **kwargs):
        self.points = kwargs.pop('points')
        super(LinesEntity, self).__init__(*args, **kwargs)

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


class CircleEntity(Entity):

    def __init__(self, *args, **kwargs):
        self.center = kwargs.pop('center')
        self.radius = kwargs.pop('radius')
        super(CircleEntity, self).__init__(*args, **kwargs)

    def draw(self, ctx, **kwargs):
        super(LineEntity, self).draw(ctx, **kwargs)

        self.transform(ctx)
        self.set_draw_settings(ctx, **kwargs)

        ctx.arc(self.center[0], self.center[1], self.radius, 0, math.pi*2)
        ctx.stroke()

    def _get_bbox(self):
        points = (point1, point2)
        xs = map(lambda p: p[0], points)
        ys = map(lambda p: p[1], points)
        return (
            min(xs), min(ys),
            max(xs)-min(xs), max(ys)-min(ys)
        )

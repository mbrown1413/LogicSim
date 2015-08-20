
from __future__ import division
import math
import os

import numpy
import cairo


class Entity(object):
    draggable = True

    def __init__(self, pos=(0, 0), scale=1, rot=0, name=""):
        self.pos = numpy.array(pos)
        self.scale = scale
        self.rot = rot
        self.name = name

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

    def draw(self, context, **kwargs):
        raise NotImplementedError()

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

    def validate(self):
        pass

    def on_activate(self):
        pass

    def __str__(self):
        name_str = ""
        if self.name:
            name_str = ' "{}"'.format(self.name)
        return "<{}{}>".format(self.__class__.__name__, name_str)


class TestEntity(Entity):

    def __init__(self, *args, **kwargs):
        super(TestEntity, self).__init__(*args, **kwargs)
        self.r = 5

    def draw(self, ctx, **kwargs):
        self.transform(ctx)
        ctx.arc(0, 0, self.r, 0, 2*math.pi)
        if kwargs.get("selected", False):
            ctx.set_source_rgb(0, 0, 1)
        else:
            ctx.set_source_rgb(0, 0, 0)
        ctx.stroke()

    def get_bbox(self):
        r = self.r + 1
        return (
            self.pos[0] - r,
            self.pos[1] - r,
            r*2, r*2
        )

    def point_intersect(self, point):
        return numpy.square(point - self.pos).sum() <= self.r**2

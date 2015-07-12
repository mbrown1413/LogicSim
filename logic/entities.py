
from __future__ import division
import math

import numpy


class Entity(object):

    def __init__(self, pos=(0, 0), scale=1, rot=0, name=""):
        self.pos = numpy.array(pos)
        self.scale = scale
        self.rot = rot
        self.name = name

    def transform(self, context):
        context.translate(*self.pos)
        context.scale(self.scale, self.scale)
        context.rotate(math.radians(self.rot))

    def draw(self, context, **kwargs):
        raise NotImplementedError()

    def get_bbox(self):
        raise NotImplementedError()

    def point_intersect(self, point):
        bbox = self.get_bbox()
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

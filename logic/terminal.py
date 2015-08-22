
import numpy


class Terminal(object):

    def __init__(self, part, name, pos, net=None, output="float"):
        self.part = part
        self.name = name
        self.pos = pos
        self.net = net
        self.output = output
        self._input = "float"

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, value):
        assert value in ("high", "low", "float", "contention")
        self._input = value

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
        return self.part.point_schematic_to_object(self.pos)

    def __str__(self):
        if self.part.name:
            return "<{}[{}]>".format(self.part.name, self.name)
        else:
            return "<{}[{}]>".format(self.part, self.name)

    __repr__ = __str__

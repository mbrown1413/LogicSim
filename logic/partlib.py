
from collections import OrderedDict
from copy import deepcopy
import json

import logic


class PartLibrary(OrderedDict):

    # See: https://wiki.python.org/moin/SubclassingDictionaries
    __slots__ = []  # No attributes

    def load_dict(self, d):
        d = deepcopy(d)
        name = d.pop('name')
        if name in self:
            raise ValueError('Duplicate part name: "{}"'.format(name))

        def create_part(**kwargs):
            schematic = logic.Schematic.from_dict(d)
            return logic.parts.AggregatePart(schematic, **kwargs)

        self[name] = create_part

    def load_file(self, filename):
        data = json.loads(open(filename, 'r').read())
        self.load_dict(data)

    def load_folder(self, path):
        raise NotImplementedError()

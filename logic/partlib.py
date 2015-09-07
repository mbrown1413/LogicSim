
from collections import OrderedDict
from copy import deepcopy
import json

import logic


class PartLibrary(OrderedDict):

    # See: https://wiki.python.org/moin/SubclassingDictionaries
    __slots__ = []  # No attributes

    def __init__(self, classes):
        mapping = []
        for cls in classes:
            assert cls.part_type is not None
            mapping.append((cls.part_type, cls))
        super(PartLibrary, self).__init__(mapping)

    def load_dict(self, d):
        d = deepcopy(d)
        part_type = d.pop('name', None)
        if not part_type:
            raise ValueError("Parts must have a name.")
        if part_type in self:
            raise ValueError('Duplicate part name: "{}"'.format(part_type))

        def create_part(**kwargs):
            schematic = logic.Schematic.from_dict(d)
            return logic.parts.AggregatePart(schematic, part_type, **kwargs)

        self[part_type] = create_part

    def load_file(self, filename):
        data = json.loads(open(filename, 'r').read())
        self.load_dict(data)

    def load_folder(self, path):
        raise NotImplementedError()

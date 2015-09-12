
import json

import numpy


class JsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, numpy.ndarray):
            return list(obj)
        super(Blah, self).default(obj)

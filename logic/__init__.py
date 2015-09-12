
from schematic import Schematic
from schematicwidget import SchematicWidget
from interface import Interface
from terminal import Terminal
from parts import Part
from net import Net, NetNode
from partlib import PartLibrary

import parts

part_library = PartLibrary((

    # Basic Circuitry
    parts.TransistorPart,
    parts.VddPart,
    parts.GndPart,
    parts.ProbePart,
    parts.SwitchPart,
    parts.IOPart,

    # Drawing
    parts.LinesPart,
    parts.CirclePart,
    parts.CurvePart,
    #text

))

import os
part_library.load_folder(
    os.path.join(os.path.dirname(__file__), "part_library")
)
del os

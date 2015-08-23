
from schematic import Schematic
from schematicwidget import SchematicWidget
from interface import Interface
from terminal import Terminal
from parts import Part
from net import Net, NetNode
from partlib import PartLibrary

import parts

part_library = PartLibrary([

    # Basic Circuitry
    ("Transistor", parts.TransistorPart),
    ("Vdd",        parts.VddPart),
    ("Gnd",        parts.GndPart),
    ("Probe",      parts.ProbePart),
    ("Switch",     parts.SwitchPart),
    ("IO",         parts.IOPart),

    # Drawing
    ("Lines", parts.LinesPart),
    ("Circle", parts.CirclePart),
    #"Text"),
    #"Curve"),

])

import os
part_library.load_file(
    os.path.join(
        os.path.dirname(__file__),
        "part_library",
        "not.schem",
    )
)
#part_library.load_folder(
#    os.path.join(os.path.dirname(__file__), "part_library")
#)
del os

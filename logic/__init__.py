
from schematic import Schematic
from schematicwidget import SchematicWidget
from interface import Interface
from terminal import Terminal
from parts import Part
from net import Net, NetNode

import parts

part_registry = {

    # Basic Circuitry
    "Transistor": parts.TransistorPart,
    "Vdd":        parts.VddPart,
    "Gnd":        parts.GndPart,
    "Probe":      parts.ProbePart,
    "Switch":     parts.SwitchPart,
    "IO":         parts.IOPart,

    # Drawing
    "Lines": parts.LinesPart,
    "Circle": parts.CirclePart,
    #"Text":
    #"Curve":

}

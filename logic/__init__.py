
from schematic import Schematic
from schematicwidget import SchematicWidget
from entities import Entity
from net import Net
from components import Component
from interface import Interface

import entities
import components

entity_registry = {

    # Basic Components
    "Transistor": components.TransistorComponent,
    "Vdd":        components.VddComponent,
    "Gnd":        components.GndComponent,
    "Probe":      components.ProbeComponent,
    "Switch":     components.SwitchComponent,
    "IO":         components.IOComponent,

    # Drawing Entities
    "Lines": entities.LinesEntity,
    "Circle": entities.CircleEntity,
    #"Text":
    #"Curve":

}

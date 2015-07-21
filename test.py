
import gtk
from gtk import gdk

import logic


def main():
    schematic = logic.Schematic()

    """
    # One Transistor
    s1 = logic.components.SwitchComponent((-50, 0))
    s2 = logic.components.SwitchComponent((10, -50))
    s3 = logic.components.SwitchComponent((10, 50))
    t1 = logic.components.TransistorEntity((0, 0), pmos=False)
    schematic.add_entities((
        s1, s2, s3, t1
    ))
    schematic.connect((t1['gate'], s1))
    schematic.connect((t1['source'], s2))
    schematic.connect((t1['drain'], s3))
    """

    """
    # Two Transistors
    s1 = logic.components.SwitchComponent((-50, 0))
    s2 = logic.components.VddComponent((10, -50))
    s3 = logic.components.ProbeComponent((10, 100))
    s4 = logic.components.SwitchComponent((-50, 50))
    t1 = logic.components.TransistorEntity((0, 0), pmos=False)
    t2 = logic.components.TransistorEntity((0, 50), pmos=False)
    schematic.add_entities((
        s1, s2, s3, s4, t1, t2
    ))
    schematic.connect((t1['gate'], s1))
    schematic.connect((t1['source'], s2))
    schematic.connect((t1['drain'], t2['source']))
    schematic.connect((t2['drain'], s3))
    schematic.connect((t2['gate'], s4))
    """

    # Not Gate
    vdd = logic.components.VddComponent((10, -70))
    gnd = logic.components.GndComponent((10, 30))
    io1 = logic.components.IOComponent((-50, -20), name="in")
    t1 = logic.components.TransistorEntity((0, 0), name="t1")
    t2 = logic.components.TransistorEntity((0, -40), name="t2", pmos=True)
    io2 = logic.components.IOComponent((50, -20), name="out")
    not_schem = logic.Schematic()
    not_schem.add_entities((
        vdd, gnd, io1, t1, t2, io2
    ))
    not_schem.connect((vdd, t2['source']))
    not_schem.connect((gnd, t1['drain']))
    not_schem.connect((io1, t1['gate'], t2['gate']))
    not_schem.connect((io2, t1['source'], t2['drain']))
    not_component = logic.components.AggregateComponent(not_schem)

    s1 = logic.components.SwitchComponent((-80, -20), outputs=('low', 'high'))
    p1 = logic.components.ProbeComponent((80, -20))
    schematic.add_entities((
        not_component, s1, p1
    ))
    schematic.connect((s1, not_component['in']))
    schematic.connect((p1, not_component['out']))


    widget = logic.SchematicWidget(schematic)

    window = gtk.Window()
    window.set_default_size(500, 500)
    window.add(widget)
    window.connect("destroy", gtk.main_quit)
    window.show_all()
    window.set_title("Logic Simulator")

    widget.pan_to_entities()

    gtk.main()

if __name__ == "__main__":
    main()

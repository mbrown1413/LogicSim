
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
    t1 = logic.components.TransistorComponent((0, 0), pmos=False)
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
    t1 = logic.components.TransistorComponent((0, 0), pmos=False)
    t2 = logic.components.TransistorComponent((0, 50), pmos=False)
    schematic.add_entities((
        s1, s2, s3, s4, t1, t2
    ))
    schematic.connect((t1['gate'], s1))
    schematic.connect((t1['source'], s2))
    schematic.connect((t1['drain'], t2['source']))
    schematic.connect((t2['drain'], s3))
    schematic.connect((t2['gate'], s4))
    """

    gate1 = logic.components.XnorGateComponent((0, 0))
    s1 = logic.components.SwitchComponent((-80, -10), outputs=('low', 'high'))
    s2 = logic.components.SwitchComponent((-80, 10), outputs=('low', 'high'))
    p1 = logic.components.ProbeComponent((80, 0))
    schematic.add_entities((
        gate1, s1, s2, p1
    ))
    schematic.connect((s1, gate1['in1']))
    schematic.connect((s2, gate1['in2']))
    schematic.connect((p1, gate1['out']))





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

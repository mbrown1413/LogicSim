
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
    vdd = logic.components.VddComponent((10, -100))
    gnd = logic.components.GndComponent((10, 50))
    s1 = logic.components.SwitchComponent((-50, 0), outputs=('low', 'high'))
    t1 = logic.components.TransistorEntity((0, 0), name="t1")
    t2 = logic.components.TransistorEntity((0, -50), name="t2", pmos=True)
    p1 = logic.components.ProbeComponent((50, -20))
    schematic.add_entities((
        vdd, gnd, s1, t1, t2, p1
    ))
    schematic.connect((vdd, t2['source']))
    schematic.connect((gnd, t1['drain']))
    schematic.connect((s1, t1['gate'], t2['gate']))
    schematic.connect((p1, t1['source'], t2['drain']))
    

    widget = logic.SchematicWidget(schematic)

    window = gtk.Window()
    window.set_default_size(500, 500)
    window.add(widget)
    window.connect("destroy", gtk.main_quit)
    window.show_all()
    window.set_title("Logic Simulator")

    # Not sure why I couldn't get this event to work directly with the widget.
    window.connect("key-press-event", lambda w, e: widget.on_key_press(widget, e))
    window.add_events(gdk.KEY_PRESS_MASK)

    widget.pan_to_entities()

    gtk.main()

if __name__ == "__main__":
    main()

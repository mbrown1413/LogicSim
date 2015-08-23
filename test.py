
import gtk
from gtk import gdk

import logic


def main():
    schematic = logic.Schematic()

    # One Transistor
    """
    s1 = logic.parts.SwitchPart((-50, 0))
    s2 = logic.parts.SwitchPart((10, -50))
    s3 = logic.parts.SwitchPart((10, 50))
    t1 = logic.parts.TransistorPart((0, 0), pmos=False)
    schematic.add_parts(
        s1, s2, s3, t1
    )
    schematic.connect(t1['gate'], s1)
    schematic.connect(t1['source'], s2)
    schematic.connect(t1['drain'], s3)
    """

    # Two Transistors
    """
    s1 = logic.parts.SwitchPart((-5, 0))
    vdd = logic.parts.VddPart((1, -5))
    s3 = logic.parts.GndPart((1, 10))
    s4 = logic.parts.SwitchPart((-5, 5))
    t1 = logic.parts.TransistorPart((0, 0), pmos=False)
    t2 = logic.parts.TransistorPart((0, 5), pmos=False)
    schematic.add_parts(
        s1, vdd, s3, s4, t1, t2
    )
    schematic.connect(t1['gate'], s1)
    schematic.connect(t1['source'], vdd)
    schematic.connect(t1['drain'], t2['source'])
    schematic.connect(t2['drain'], s3)
    schematic.connect(t2['gate'], s4)
    """

    # 1-input Gate
    """
    gate = logic.parts.NotGatePart((0, 0))
    s1 = logic.parts.SwitchPart((-8, 0), outputs=('low', 'high'))
    p1 = logic.parts.ProbePart((8, 0))
    schematic.add_parts(
        gate, s1, p1
    )
    schematic.connect(s1, gate['in'])
    schematic.connect(p1, gate['out'])
    """

    schematic = logic.Schematic.from_json_str("""
    {
        "parts": [
            {
                "type": "Switch",
                "name": "s1",
                "pos": [-4, 0]
            }, {
                "type": "Not",
                "name": "not"
            }, {
                "type": "Probe",
                "name": "p1",
                "pos": [8, 0]
            }
        ],
        "nets": [
            {
                "nodes": [
                    {"location": "s1", "neighbors": [1]},
                    {"location": "not[in]", "neighbors": [0]}
                ]
            }, {
                "nodes": [
                    {"location": "not[out]", "neighbors": [1]},
                    {"location": "p1", "neighbors": [0]}
                ]
            }
        ]
    }
    """)
    #gate = logic.parts.NotGatePart((0, 0))
    #schematic.add_part(gate)

    # 2-input Gate
    """
    gate1 = logic.parts.NorGatePart((0, 0))
    s1 = logic.parts.SwitchPart((-8, -2), outputs=('low', 'high'))
    s2 = logic.parts.SwitchPart((-8, 2), outputs=('low', 'high'))
    p1 = logic.parts.ProbePart((8, 0))
    schematic.add_parts(
        gate1, s1, s2, p1
    )
    schematic.connect(s1, (-4, -2), (-4, -1), gate1['in1'])
    schematic.connect(s2, (-4,  2), (-4,  1), gate1['in2'])
    schematic.connect(p1, gate1['out'])
    """




    interface = logic.Interface(schematic)
    interface.run()

if __name__ == "__main__":
    main()


from collections import OrderedDict

import gtk

import logic


class Interface(gtk.Window):

    def __init__(self, schematic=None):
        super(Interface, self).__init__()

        if schematic is None:
            schematic = logic.Schematic()
        self.schematic = schematic
        self.schematic_widget = logic.SchematicWidget(self.schematic)

        menu_description = OrderedDict((
            ("File", OrderedDict((
                ("Open", lambda _: None),
                ("Save", lambda _: None),
                ("Exit", gtk.main_quit),
            ))),
            ("View", OrderedDict((
                ("Grid Size +", lambda _: self.schematic_widget.change_grid_size(2)),
                ("Grid Size -", lambda _: self.schematic_widget.change_grid_size(0.5)),
            ))),
            ("Add", OrderedDict()),  # Filled in later automatically
            ("Part", OrderedDict((
                ("Size +", lambda _: self.schematic_widget.change_part_scale(2)),
                ("Size -", lambda _: self.schematic_widget.change_part_scale(0.5)),
            ))),
        ))

        part_classes = {
            "Transistor": logic.parts.TransistorPart,
            "Vdd": logic.parts.VddPart,
            "Gnd": logic.parts.GndPart,
            "Probe": logic.parts.ProbePart,
            "Switch": logic.parts.SwitchPart,
        }
        def new_part_func(menu):
            cls_name = menu.get_label()
            #TODO: Wow... talk about inefficient
            for name, cls in part_classes.iteritems():
                if name == cls_name:
                    self.schematic_widget.add_part(cls())
                    break
        for name, part_cls in part_classes.iteritems():
            menu_description["Add"][name] = new_part_func

        self.menu_bar = gtk.MenuBar()
        for menu_name, menu_dict in menu_description.iteritems():
            menu = gtk.Menu()
            title_item = gtk.MenuItem(menu_name)
            title_item.set_submenu(menu)
            for item_name, item_action in menu_dict.iteritems():
                menu_item = gtk.MenuItem(item_name)
                menu_item.connect("activate", item_action)
                menu.append(menu_item)
            self.menu_bar.append(title_item)

        vbox = gtk.VBox(False, 0)
        vbox.pack_start(self.menu_bar, False, False, 0)
        vbox.pack_start(self.schematic_widget, True, True, 0)
        self.add(vbox)

        self.set_default_size(500, 500)
        self.connect("destroy", gtk.main_quit)
        self.set_title("Logic Simulator")
        self.show_all()

        self.schematic_widget.pan_to_parts()

    def run(self):
        gtk.main()

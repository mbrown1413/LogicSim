
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
                ("Grid Size +", lambda _: self.schematic_widget.grid_size_up()),
                ("Grid Size -", lambda _: self.schematic_widget.grid_size_down()),
            ))),
            ("Add", OrderedDict()),  # Filled in later automatically
        ))

        entity_classes = (
            logic.components.TransistorComponent,
            logic.components.VddComponent,
            logic.components.GndComponent,
            logic.components.ProbeComponent,
            logic.components.SwitchComponent,
        )
        def new_entity_func(menu):
            cls_name = menu.get_label()
            #TODO: Wow... talk about inefficient
            for cls in entity_classes:
                if cls.name == cls_name:
                    self.schematic_widget.add_entity(cls())
                    break
        for entity_cls in entity_classes:
            menu_description["Add"][entity_cls.name] = new_entity_func

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

        self.schematic_widget.pan_to_entities()

    def run(self):
        gtk.main()


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
                ("New", lambda _: self.load_schematic(logic.Schematic())),
                ("Open", lambda _: self.menu_load()),
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

        part_classes = dict(logic.part_library)
        del part_classes['Lines']
        del part_classes['Circle']
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

        self.vbox = gtk.VBox(False, 0)
        self.vbox.pack_start(self.menu_bar, False, False, 0)
        self.vbox.pack_start(self.schematic_widget, True, True, 0)
        self.add(self.vbox)

        self.set_default_size(500, 500)
        self.connect("destroy", gtk.main_quit)
        self.set_title("Logic Simulator")
        self.show_all()

    def menu_load(self):

        dialog = gtk.FileSelection("Open Schematic...")
        def ok_clicked(w):
            filename = dialog.get_filename()
            self.load_schematic_from_file(filename)
            dialog.destroy()
        dialog.ok_button.connect("clicked", ok_clicked)
        dialog.cancel_button.connect("clicked", lambda _: dialog.destroy())
        dialog.show()

    def load_schematic_from_file(self, filename):
        schematic = logic.Schematic.from_file(filename)
        self.load_schematic(schematic)

    def load_schematic(self, schematic):
        self.schematic = schematic
        old_widget = self.schematic_widget
        self.schematic_widget = logic.SchematicWidget(schematic)

        # Replace old widget with new
        self.vbox.remove(old_widget)
        self.vbox.pack_start(self.schematic_widget, True, True, 0)
        self.show_all()

    def run(self):
        gtk.main()


import os
import json
from collections import OrderedDict

import gtk

import logic
import _json


class Interface(gtk.Window):

    def __init__(self, schematic=None, filename=None):
        super(Interface, self).__init__()
        self.filename = filename

        if schematic is None:
            schematic = logic.Schematic()
        self.schematic = schematic
        self.schematic_widget = logic.SchematicWidget(self.schematic)

        menu_description = OrderedDict((
            ("File", OrderedDict((
                ("New", lambda _: self.menu_new()),
                ("Open", lambda _: self.menu_open()),
                ("Save", lambda _: self.menu_save()),
                ("Save As...", lambda _: self.menu_save_as()),
                ("Exit", gtk.main_quit),
            ))),
            ("View", OrderedDict((
                ("Grid Size +", lambda _: self.schematic_widget.change_grid_size(2)),
                ("Grid Size -", lambda _: self.schematic_widget.change_grid_size(0.5)),
                ("Fit View", lambda _: self.schematic_widget.fit_view()),
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

    def save_schematic(self, filename):
        contents = json.dumps(self.schematic.get_dict(), indent=4, cls=_json.JsonEncoder)
        open(filename, "w").write(contents)

    def run(self):
        gtk.main()

    def menu_new(self):
        self.load_schematic(logic.Schematic())
        self.filename = None

    def menu_open(self):
        dialog = gtk.FileChooserDialog("Open Schematic...")
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)

        try:
            result = dialog.run()
            self.filename = dialog.get_filename()
        finally:
            dialog.destroy()

        if result == gtk.RESPONSE_OK:
            self.load_schematic_from_file(self.filename)

    def menu_save(self):
        if self.filename is None:
            self.menu_save_as()
            return

        self.save_schematic(self.filename)

    def menu_save_as(self):
        dialog = gtk.FileChooserDialog("Save As...", action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        try:
            result = dialog.run()
            path = dialog.get_filename()
        finally:
            dialog.destroy()

        if result == gtk.RESPONSE_OK:

            if os.path.exists(path) and not self.dialog_confirm_save(path):
                return

            self.save_schematic(path)
            self.filename = path

    def dialog_confirm_save(self, filename):
        dialog = gtk.MessageDialog(self,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_NONE,
            'File "{}" already exists. Overwrite?'.format(filename)
        )
        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)

        try:
            response = dialog.run()
        finally:
            dialog.destroy()

        return response == gtk.RESPONSE_OK

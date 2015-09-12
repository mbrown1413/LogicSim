
from __future__ import division

import numpy
import gtk
from gtk import gdk
import cairo

import logic

# There are 2 different coordinate spaces used in SchematicWidget: widget-space
# and draw-space.
#
# Widget-Space: pixel coordinates that the widget is drawn in. Usually passed
#     around as x and y variables, since they are mostly used to interact with
#     GTK.
# Draw-Space: This is the canvas that the widget gives a moving-window view
#     into. Usually passed around as a `numpy.array((x, y))`.
#
# Conversion between the two spaces can be done by pos_draw_to_widget() and
# pos_widget_to_draw().

class SchematicWidget(gtk.DrawingArea):
    MIN_SCALE = 0.2

    def __init__(self, schematic):
        gtk.DrawingArea.__init__(self)
        self.schematic = schematic
        self.draw_pos = numpy.array((0, 0))  # Widget-space coordinate of the
                                             # upper left corner of the canvas
        self.first_exposure = True
        self.scale = 20
        self.grid_size = 1

        self.connect("expose_event", self.on_expose)

        # State variables typically modified by action classes
        self.selected = None
        self.dragging = False
        self.grid_visible = True
        self.ghost_part = None  # Drawn, but not actually in schematic
        self.draw_all_terminals = False

        self.action_listeners = (

            # Mouse Actions
            NetCreateAction(mouse_button=1),
            NetDragNodeAction(mouse_button=1),
            PartDragAction(mouse_button=1),
            PanDragAction(mouse_button=1),
            SelectAction(mouse_button=1),
            NetAddNodeAction(mouse_button=2),

            ZoomAction(),

            # Keyboard Actions
            DeleteAction(key=65535),  # Delete key
            PanAction(
                left=65361, up=65362, right=65363, down=65364),  # Arrow Keys
            SimpleActions(),  # Catch-all for a lot of simple keypresses

        )
        for action in self.action_listeners:
            action.register(self)

        #TODO: For now, going to listen to all events, since I don't care about
        #      efficiency. Correctness is more important.
        self.add_events(gdk.ALL_EVENTS_MASK)

        # Needed for keyboard events. See docs for gtk.DrawingArea
        self.set_can_focus(True)

        self.schematic.reset()
        self.schematic.update()
        self.post_redraw()

    def on_expose(self, widget, event):
        #TODO: Maybe not nessesary to validate on every exposure
        self.schematic.validate()

        if self.first_exposure:
            self.first_exposure = False
            self.fit_view()

        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()

        context.translate(*self.draw_pos)
        context.scale(self.scale, self.scale)

        # Draw grid, but only if it's not too costly
        draw_area = event.area[2]*event.area[3] / self.scale**2
        n_grid_points = draw_area / self.grid_size**2
        if n_grid_points < 5000:
            self.draw_grid(context, event.area, self.grid_size)

        self.schematic.draw(context,
            selected=(self.selected,),
            draw_terminals=self.draw_all_terminals,
        )

        if self.ghost_part:
            self.ghost_part.draw(context)

        """
        if self.selected:
            context.rectangle(*self.selected.get_bbox())
            context.set_source_rgb(0, 1, 0)
            context.set_line_width(0.01)
            context.stroke()
        """

    def pos_widget_to_draw(self, x, y):
        return (numpy.array((x, y)) - self.draw_pos) / self.scale

    def pos_draw_to_widget(self, widget_pos):
        return numpy.array(widget_pos)*self.scale + self.draw_pos

    def draw_grid(self, ctx, rect, step):
        line_width = 0.07 * step

        # Convert rect from widget to draw space
        rect = (
            self.pos_widget_to_draw(rect[0], rect[1])[0],
            self.pos_widget_to_draw(rect[0], rect[1])[1],
            rect[2] / self.scale, rect[3] / self.scale
        )

        start_x = int(rect[0] / self.grid_size) * self.grid_size
        start_y = int(rect[1] / self.grid_size) * self.grid_size
        x_range = numpy.arange(start_x, rect[0]+rect[2]+line_width, step)
        y_range = numpy.arange(start_y, rect[1]+rect[3]+line_width, step)

        for x in x_range:
            for y in y_range:
                ctx.move_to(x, y)
                ctx.line_to(x, y)

        old_line_cap = ctx.get_line_cap()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(line_width)
        ctx.set_source_rgb(0, 0, 0)
        ctx.stroke()

        ctx.set_line_cap(old_line_cap)

    def zoom(self, value, center=None):
        # Center given in widget-space, or None for center of widget
        if center is None:
            _, _, width, height = self.get_allocation()
            center = (width/2, height/2)

        before = self.pos_widget_to_draw(*center)
        self.scale += value
        self.scale = max(self.MIN_SCALE, self.scale)
        after = self.pos_widget_to_draw(*center)
        self.draw_pos -= (before - after) * self.scale
        self.post_redraw()

    def zoom_set(self, value):
        self.scale = max(value, self.MIN_SCALE)
        self.post_redraw()

    def pan(self, delta_x, delta_y):
        self.draw_pos += (delta_x, delta_y)
        self.post_redraw()

    def pan_to(self, draw_pos):
        _, _, width, height = self.get_allocation()
        self.draw_pos = (width/2, height/2) - self.pos_draw_to_widget(draw_pos)
        self.post_redraw()

    def fit_view(self, parts=None):
        if parts is None: parts = self.schematic.parts
        if not parts: return

        left = top = float("inf")
        right = bot = float("-inf")
        for part in parts:
            bbox = part.get_bbox()
            left = min(left, bbox[0])
            right = max(right, bbox[0]+bbox[2])
            top = min(top, bbox[1])
            bot = max(bot, bbox[1]+bbox[3])
        center = ((left+right)/2, (top+bot)/2)
        box_w = right - left
        box_h = bot - top
        _, _, win_w, win_h = self.get_allocation()

        self.pan_to(center)
        self.scale = -5 + min(
            win_w / box_w,
            win_h / box_h,
        )

    def post_redraw(self):
        if self.window:
            x, y, w, h = self.get_allocation()
            rect = gdk.Rectangle(0, 0, w, h)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    def add_part(self, part, pos=None):
        if pos == None:
            _, _, width, height = self.get_allocation()
            pos = self.snap_to_grid(self.pos_widget_to_draw(width/2, height/2))
        part.pos = pos

        self.schematic.add_part(part)
        self.post_redraw()

    def snap_to_grid(self, pos, grid_size=None):
        if grid_size is None:
            grid_size = self.grid_size
        return numpy.array((
            round(pos[0] / self.grid_size) * grid_size,
            round(pos[1] / self.grid_size) * grid_size,
        ))

    def change_grid_size(self, factor):
        self.grid_size *= factor
        self.post_redraw()

    def change_part_scale(self, factor):
        if isinstance(self.selected, logic.Part):
            self.selected.scale *= factor
            self.post_redraw()


class BaseAction(object):
    EVENT_FUNCS = {
        "expose_event": "on_expose",
        "motion-notify-event": "on_movement",
        "button-press-event": "on_button_press",
        "button-release-event": "on_button_release",
        "key-press-event": "on_key_press",
        "scroll-event": "on_scroll",
    }

    # Subclasses overwrite this to make specific keyword arguments show up as
    # attributes.
    parameters = ()

    def __init__(self, **kwargs):
        for k in self.parameters:
            assert k in kwargs
        for k, v in kwargs.iteritems():
            assert k in self.parameters
            setattr(self, k, v)

    def register(self, widget):
        self.widget = widget

        for event_name, func_name in self.EVENT_FUNCS.iteritems():
            if hasattr(self, func_name):
                self.widget.connect(event_name, getattr(self, func_name))


class SelectAction(BaseAction):
    parameters = ("mouse_button",)

    def on_button_release(self, widget, event):

        if event.button == self.mouse_button:
            pos = widget.pos_widget_to_draw(event.x, event.y)
            widget.selected = widget.schematic.part_at_pos(pos)
            widget.post_redraw()
            return True

class DeleteAction(BaseAction):
    parameters = ("key",)

    def on_key_press(self, widget, event):
        if event.keyval == self.key and widget.selected is not None:
            widget.schematic.remove(widget.selected)
            widget.selected = None
            widget.post_redraw()

class BaseDragAction(BaseAction):
    parameters = ("mouse_button",)

    def __init__(self, **kwargs):
        super(BaseDragAction, self).__init__(**kwargs)
        self.dragging = False
        self.waiting_for_drag = False

    def on_button_press(self, widget, event):
        if event.button == self.mouse_button and not widget.dragging:
            self.waiting_for_drag = True

    def on_movement(self, widget, event):

        if self.waiting_for_drag:
            self.waiting_for_drag = False
            if widget.dragging:
                self.dragging = False
            else:
                self.dragging = self.should_start_drag(widget, event)
                assert self.dragging in (True, False)

            if self.dragging:
                self.widget.dragging = True
                self.on_drag_start(widget, event)

                # Propagate event to other handlers so they can realize a
                # different action started a drag. Without this, other drag
                # actions would consider dragging as soon as this one stopped,
                # being unaware of any of the events that happened during this
                # drag.
                return False

        if self.dragging:
            self.on_drag_movement(widget, event)
            return True

    def on_button_release(self, widget, event):
        if event.button == self.mouse_button:
            self.waiting_for_drag = False

            if self.dragging:
                self.dragging = False
                widget.dragging = False
                self.on_drag_end(widget, event)
                return True

    def should_start_drag(self, widget, event):
        return True

    def on_drag_start(self, widget, event):
        pass

    def on_drag_movement(self, widget, event):
        pass

    def on_drag_end(self, widget, event):
        pass

class PanDragAction(BaseDragAction):

    def on_drag_start(self, widget, event):
        self.prev_mouse_pos = numpy.array((event.x, event.y))
        widget.grid_visible = False

    def on_drag_movement(self, widget, event):
        mouse_pos = numpy.array((event.x, event.y))
        delta = mouse_pos - self.prev_mouse_pos
        widget.draw_pos += delta
        self.prev_mouse_pos = mouse_pos
        widget.post_redraw()

    def on_drag_end(self, widget, event):
        widget.grid_visible = True
        widget.post_redraw()

class PartDragAction(BaseDragAction):

    def should_start_drag(self, widget, event):
        return widget.selected is not None and \
               widget.selected.draggable and \
               widget.selected.point_intersect(
                   widget.pos_widget_to_draw(event.x, event.y)
               )

    def on_drag_start(self, widget, event):
        self.start_part_pos = tuple(widget.selected.pos)
        self.start_mouse_pos = widget.pos_widget_to_draw(event.x, event.y)

    def on_drag_movement(self, widget, event):
        mouse_pos = widget.pos_widget_to_draw(event.x, event.y)
        delta = mouse_pos - self.start_mouse_pos
        widget.selected.pos = widget.snap_to_grid(self.start_part_pos + delta)

        widget.post_redraw()

    def on_drag_end(self, widget, event):
        self.start_part_pos = None
        self.start_mouse_pos = None

class NetCreateAction(BaseDragAction):

    def should_start_drag(self, widget, event):
        if not isinstance(widget.selected, logic.Part):
            return False
        part = widget.selected

        draw_pos = widget.pos_widget_to_draw(event.x, event.y)
        terminal = part.point_intersect_terminals(draw_pos)
        if terminal:
            self.start_term = terminal
            self.start_pos = terminal.absolute_pos
            return True

        return False

    def on_drag_start(self, widget, event):
        widget.draw_all_terminals = True

    def on_drag_movement(self, widget, event):
        pos = self.widget.pos_widget_to_draw(event.x, event.y)
        term = widget.schematic.get_closest_terminal(pos, search_dist=0.5*self.start_term.part.scale)
        if term:
            end_pos = term.absolute_pos
        else:
            end_pos = widget.pos_widget_to_draw(event.x, event.y)

        widget.ghost_part = logic.Net(self.start_pos, end_pos, scale=self.start_term.part.scale)
        widget.post_redraw()

    def on_drag_end(self, widget, event):
        pos = self.widget.pos_widget_to_draw(event.x, event.y)
        end_term = widget.schematic.get_closest_terminal(pos, search_dist=0.5)

        if end_term and end_term != self.start_term:
            widget.schematic.connect(self.start_term, end_term)
            widget.schematic.update()
            widget.post_redraw()

        widget.draw_all_terminals = False
        widget.ghost_part = None
        widget.post_redraw()

class NetAddNodeAction(BaseAction):
    parameters = ("mouse_button",)

    def on_button_release(self, widget, event):
        if event.button != self.mouse_button or \
                not isinstance(widget.selected, logic.Net):
            return False

        net = widget.selected
        pos = widget.pos_widget_to_draw(event.x, event.y)
        intersection = net.point_intersect(pos)
        if intersection is not False:
            node_idx1, node_idx2, point = intersection
            net.add_floating_node(node_idx1, node_idx2, point)
            widget.post_redraw()
            return True

class NetDragNodeAction(BaseDragAction):

    def should_start_drag(self, widget, event):
        if not isinstance(widget.selected, logic.Net):
            return False

        net = widget.selected
        draw_pos = widget.pos_widget_to_draw(event.x, event.y)
        node = net.point_intersect_nodes(draw_pos)
        if node and node.internal:
            self.net = net
            self.node = node
            return True

        return False

    def on_drag_movement(self, widget, event):
        draw_pos = widget.pos_widget_to_draw(event.x, event.y)
        self.node.pos = widget.snap_to_grid(draw_pos)
        widget.post_redraw()

    def on_drag_end(self, widget, event):
        self.net.simplify_nodes()

class PanAction(BaseAction):
    parameters = ("left", "up", "right", "down",)

    ARROW_KEY_PAN_AMOUNT = 10

    def on_key_press(self, widget, event):
        if event.keyval == self.left:  # Left
            widget.pan(self.ARROW_KEY_PAN_AMOUNT, 0)
        elif event.keyval == self.up:  # Up
            widget.pan(0, self.ARROW_KEY_PAN_AMOUNT)
        elif event.keyval == self.right:  # Right
            widget.pan(-self.ARROW_KEY_PAN_AMOUNT, 0)
        elif event.keyval == self.down:  # Down
            widget.pan(0, -self.ARROW_KEY_PAN_AMOUNT)

class ZoomAction(BaseAction):
    ZOOM_AMOUNT = 2

    def on_scroll(self, widget, event):
        if event.state & gdk.CONTROL_MASK and event.direction in (gdk.SCROLL_UP, gdk.SCROLL_DOWN):
            amount = self.ZOOM_AMOUNT if event.direction == gdk.SCROLL_UP else -self.ZOOM_AMOUNT
            widget.zoom(amount, numpy.array((event.x, event.y)))
            widget.post_redraw()
            return True

    def on_key_press(self, widget, event):
        if event.keyval == ord(']'):
            widget.zoom(self.ZOOM_AMOUNT)
        elif event.keyval == ord('['):
            widget.zoom(-self.ZOOM_AMOUNT)

class SimpleActions(BaseAction):
    """
    An aggregate of simple actions that don't deserve the length of a separate
    class.

    Is this just me being lazy, or is it good design? We may never know.
    """

    def on_key_press(self, widget, event):

        if event.keyval == ord('r'):  # Reset Simulation
            widget.schematic.reset()
            #widget.schematic.update()
            widget.post_redraw()

        elif event.keyval == ord('u'):  # Update Simulation
            widget.schematic.update()
            widget.post_redraw()

        elif event.keyval == ord('='):  # Reset Zoom
            widget.zoom_set(1)

        elif event.keyval == ord(' '):  # Activate part
            if isinstance(widget.selected, logic.Part):
                widget.selected.on_activate()
                widget.schematic.update()
                widget.post_redraw()

        elif event.keyval == ord('R'):  # Rotate
            if isinstance(widget.selected, logic.Part):
                widget.selected.rotate(90)
                widget.post_redraw()

    def on_button_release(self, widget, event):
        if event.button == 2:
            pos = widget.pos_widget_to_draw(event.x, event.y)
            part = widget.schematic.part_at_pos(pos)
            if isinstance(part, logic.Part):
                part.on_activate()
                widget.schematic.update()
                widget.post_redraw()
                return True

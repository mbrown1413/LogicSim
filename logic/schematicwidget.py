
from __future__ import division

import numpy
import gtk
from gtk import gdk
import cairo

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

        # Widget-space coordinate of the upper left corner of the canvas
        self.draw_pos = numpy.array((0, 0))
        self.scale = 2

        self.connect("expose_event", self.on_expose)

        self.selected = None
        self.dragging = False
        self.grid_visible = True

        self.action_listeners = (

            # Mouse Actions
            EntityDragAction(mouse_button=1),
            PanDragAction(mouse_button=1),
            SelectAction(mouse_button=1),

            ZoomAction(),

            # Keyboard Actions
            DeleteAction(key=65535),  # Delete key
            EntityPanAction(
                left=65361, up=65362, right=65363, down=65364),  # Arrow Keys
            SimpleActions(),  # Catch-all for a lot of simple keypresses

        )
        for action in self.action_listeners:
            action.register(self)

        #self.add_events(gdk.POINTER_MOTION_MASK)
        #self.add_events(gdk.BUTTON_PRESS_MASK)
        #self.add_events(gdk.BUTTON_RELEASE_MASK)
        #self.add_events(gdk.KEY_PRESS_MASK)
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

        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()

        context.translate(*self.draw_pos)
        context.scale(self.scale, self.scale)

        if self.grid_visible and self.scale > 0.8:
            self.draw_grid(context, event.area)
        self.schematic.draw(context, selected_entities=(self.selected,))

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

    def draw_grid(self, ctx, rect, step=10, grid_type="dots"):
        assert isinstance(step, int)

        # Convert rect from widget to draw space
        rect = (
            self.pos_widget_to_draw(rect[0], rect[1])[0],
            self.pos_widget_to_draw(rect[0], rect[1])[1],
            rect[2] / self.scale, rect[3] / self.scale
        )

        {
            "dots": self.draw_grid_dots,
            "lines": self.draw_grid_lines,
        }[grid_type](ctx, rect, step)

    def draw_grid_lines(self, ctx, rect, step):
        line_width = 0.3

        # Vertical Lines
        start_x = int(rect[0]) - int(rect[0])%step
        for x in numpy.arange(start_x, rect[0]+rect[2]+line_width, step):
            ctx.move_to(x, rect[1])
            ctx.line_to(x, rect[1]+rect[3])

        # Horizontal Lines
        start_y = int(rect[1]) - int(rect[1])%step
        for y in numpy.arange(start_y, rect[1]+rect[3]+line_width, step):
            ctx.move_to(rect[0], y)
            ctx.line_to(rect[0]+rect[2], y)

        ctx.set_line_width(line_width)
        ctx.set_source_rgb(0, 1.0, 0)
        ctx.stroke()

    def draw_grid_dots(self, ctx, rect, step):
        old_line_cap = ctx.get_line_cap()
        line_width = 0.7

        start_x = int(rect[0]) - int(rect[0])%step
        start_y = int(rect[1]) - int(rect[1])%step
        x_range = numpy.arange(start_x, rect[0]+rect[2]+line_width, step)
        y_range = numpy.arange(start_y, rect[1]+rect[3]+line_width, step)
        for x in x_range:
            for y in y_range:
                ctx.move_to(x, y)
                ctx.line_to(x, y)

        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(line_width)
        ctx.set_source_rgb(0, 0.0, 0)
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

    def entity_at_pos(self, draw_pos):
        for entity in self.schematic.entities:
            if entity.point_intersect(draw_pos):
                return entity
        return None

    def pan(self, delta_x, delta_y):
        self.draw_pos += (delta_x, delta_y)
        self.post_redraw()

    def pan_to(self, draw_pos):
        _, _, width, height = self.get_allocation()
        self.draw_pos = (width/2, height/2) - self.pos_draw_to_widget(draw_pos)
        self.post_redraw()

    def pan_to_entities(self, entities=None):
        if entities is None: entities = self.schematic.entities

        left = top = float("inf")
        right = bot = float("-inf")
        for entity in entities:
            bbox = entity.get_bbox()
            left = min(left, bbox[0])
            right = max(right, bbox[0]+bbox[2])
            top = min(top, bbox[1])
            bot = max(bot, bbox[1]+bbox[3])
        center = ((left+right)/2, (top+bot)/2)

        self.pan_to(center)

    def post_redraw(self):
        if self.window:
            x, y, w, h = self.get_allocation()
            rect = gdk.Rectangle(0, 0, w, h)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)


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

        if event.button == 1:
            pos = widget.pos_widget_to_draw(event.x, event.y)
            widget.selected = widget.entity_at_pos(pos)
            widget.post_redraw()
            return True

class DeleteAction(BaseAction):
    parameters = ("key",)

    def on_key_press(self, widget, event):
        if event.keyval == self.key and widget.selected:
            widget.schematic.remove_entity(widget.selected)
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

class EntityDragAction(BaseDragAction):

    def should_start_drag(self, widget, event):
        return widget.selected is not None and \
               widget.selected.point_intersect(
                   widget.pos_widget_to_draw(event.x, event.y)
               )

    def on_drag_start(self, widget, event):
        self.start_entity_pos = tuple(widget.selected.pos)
        self.start_mouse_pos = widget.pos_widget_to_draw(event.x, event.y)

    def on_drag_movement(self, widget, event):
        GRID_SIZE = 10
        mouse_pos = widget.pos_widget_to_draw(event.x, event.y)
        delta = numpy.round((mouse_pos - self.start_mouse_pos) / GRID_SIZE)
        widget.selected.pos = self.start_entity_pos + delta*GRID_SIZE

        widget.post_redraw()

    def on_drag_end(self, widget, event):
        self.start_entity_pos = None
        self.start_mouse_pos = None

class EntityPanAction(BaseAction):
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
    ZOOM_AMOUNT = 0.4

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

        elif event.keyval == ord(' '):  # Activate entity
            if widget.selected:
                widget.selected.on_activate()
                widget.schematic.update()
                widget.post_redraw()

        elif event.keyval == ord('R'):  # Rotate
            if widget.selected:
                widget.selected.rotate(90)
                widget.post_redraw()

    def on_button_release(self, widget, event):
        if event.button == 2:
            pos = widget.pos_widget_to_draw(event.x, event.y)
            entity = widget.entity_at_pos(pos)
            if entity:
                entity.on_activate()
                widget.schematic.update()
                widget.post_redraw()
                return True

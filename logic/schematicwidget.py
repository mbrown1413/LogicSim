
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
    ARROW_KEY_PAN_AMOUNT = 10

    def __init__(self, schematic):
        gtk.DrawingArea.__init__(self)

        self.schematic = schematic
        # Widget-space coordinate of the upper left corner of the canvas
        self.draw_pos = numpy.array((0, 0))
        self.prev_mouse_pos = None  # Widget-space
        self.dragged = False
        self.selected = None
        self.scale = 2
        self.dragging_entity = None

        self.connect("expose_event", self.on_expose)
        self.connect("motion-notify-event", self.on_movement)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("scroll-event", self.on_scroll)

        self.add_events(gdk.POINTER_MOTION_MASK)
        self.add_events(gdk.BUTTON_PRESS_MASK)
        self.add_events(gdk.BUTTON_RELEASE_MASK)
        self.add_events(gdk.KEY_PRESS_MASK)
        #self.add_events(gdk.ALL_EVENTS_MASK)

        self.schematic.tick()
        self.post_redraw()

    def on_expose(self, widget, event):
        self.schematic.validate()

        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()

        context.translate(*self.draw_pos)
        context.scale(self.scale, self.scale)
        #context.scale(WIDTH/1.0, HEIGHT/1.0) # Normalizing the canvas

        if not self.dragged:
            self.draw_grid(context, event.area)
        self.schematic.draw(context, selected_entities=(self.selected,))

        """
        if self.selected:
            context.rectangle(*self.selected.get_bbox())
            context.set_source_rgb(0, 1, 0)
            context.set_line_width(0.01)
            context.stroke()
        """

    def on_movement(self, widget, event):
        self.dragged = True

        if not event.state & gdk.BUTTON1_MASK:
            self.prev_mouse_pos = None
            return

        mouse_pos = numpy.array([event.x, event.y])
        if self.prev_mouse_pos is None:
            self.prev_mouse_pos = mouse_pos
            return True
        delta = mouse_pos - self.prev_mouse_pos

        if self.dragging_entity:
            self.dragging_entity.pos += delta / self.scale
        else:
            self.draw_pos += delta

        if not (delta == 0).all():
            self.post_redraw()
        self.prev_mouse_pos = mouse_pos
        return True

    def on_button_press(self, widget, event):
        self.dragged = False

        if self.selected and event.button == 1 and \
                    self.selected.point_intersect(self.pos_widget_to_draw(event.x, event.y)):
            self.dragging_entity = self.selected

    def on_button_release(self, widget, event):
        self.dragging_entity = None

        if not self.dragged and event.button == 1:
            pos = self.pos_widget_to_draw(event.x, event.y)
            self.selected = self.entity_at_pos(pos)
            self.post_redraw()
            return True
        elif event.button == 1:
            self.dragged = False
            self.post_redraw()

        if event.button == 2:
            pos = self.pos_widget_to_draw(event.x, event.y)
            entity = self.entity_at_pos(pos)
            if entity:
                entity.on_activate()
                self.schematic.tick()
                self.post_redraw()
                return True

        return False

    def on_key_press(self, widget, event):
        if event.keyval == ord(']'):
            self.zoom(.4)
        elif event.keyval == ord('['):
            self.zoom(-.4)
        elif event.keyval == ord('='):
            self.zoom_set(1)
        elif event.keyval == 65535:  # Delete
            if self.selected:
                self.schematic.remove_entity(self.selected)
                self.selected = None
                self.post_redraw()
        elif event.keyval == 65361:  # Left
            self.pan(self.ARROW_KEY_PAN_AMOUNT, 0)
            self.post_redraw()
        elif event.keyval == 65362:  # Up
            self.pan(0, self.ARROW_KEY_PAN_AMOUNT)
            self.post_redraw()
        elif event.keyval == 65363:  # Right
            self.pan(-self.ARROW_KEY_PAN_AMOUNT, 0)
            self.post_redraw()
        elif event.keyval == 65364:  # Down
            self.pan(0, -self.ARROW_KEY_PAN_AMOUNT)
            self.post_redraw()

        elif event.keyval == ord('r'):
            self.schematic.reset()
            self.schematic.tick()
            self.post_redraw()
        elif event.keyval == ord('t'):
            self.schematic.tick()
            self.post_redraw()
        elif event.keyval == ord(' '):
            if self.selected:
                self.selected.on_activate()
                self.schematic.tick()
                self.post_redraw()

        elif event.keyval == ord('R'):
            if self.selected:
                self.selected.rotate(90)
                self.post_redraw()

        return False

    def on_scroll(self, widget, event):

        if event.state & gdk.CONTROL_MASK and event.direction in (gdk.SCROLL_UP, gdk.SCROLL_DOWN):
            amount = 0.4 if event.direction == gdk.SCROLL_UP else -0.4
            self.zoom(amount, numpy.array((event.x, event.y)))
            self.dragged = False
            self.post_redraw()
            return True

        return False

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

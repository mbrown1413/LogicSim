
import logic


class Net(object):

    def __init__(self, terminals):
        assert len(terminals) >= 2
        self.terminals = []
        self._output = "float"

        for term in terminals:
            if isinstance(term, logic.Component):
                # Single terminal component was given
                if len(term.terminals) != 1:
                    raise ValueError("Components can only be treated as terminals if the component has only one terminal.")
                term = term.terminals.values()[0]
            self.terminals.append(term)
            term.connect(self)

    def draw(self, context):
        first_iteration = True
        context.set_line_width(0.1)
        for term in self.terminals:
            context.save()

            term.component.transform(context)
            if first_iteration:
                context.move_to(*term.pos)
            else:
                context.line_to(*term.pos)

            context.restore()
            first_iteration = False

        context.set_source_rgb(*{
            "high": (0, 1, 0),
            "low": (0, 0, 0),
            "contention": (1, 0, 0),
            "float": (0.7, 0.7, 0.7),
        }[self._output])

        context.stroke()

    def get_bbox(self):
        left = top = float('inf')
        right = bot = float('-inf')
        for term in self.terminals:
            left = min(left, term.pos[0])
            top = min(top, term.pos[1])
            right = max(right, term.pos[0])
            bot = max(bot, term.pos[1])
        return (left, top, right-left, bot-left)

    def update(self):

        def combine(terms):
            output = "float"
            states = [term.output for term in terms]
            for state in states:
                if state in ("high", "low"):
                    if output in ("high", "low") and state != output:
                        return "contention"
                    else:
                        output = state
                elif state == "contention":
                    return "contention"
            return output

        was_updated = False
        for term in self.terminals:
            # Consider the input to each terminal by looking at every terminal
            # but the one in question. This way no feedback effects can happen
            # where a terminal affects itself.
            others = set(self.terminals)
            others.remove(term)

            prev = term.input
            term.input = combine(others)
            if term.input != prev:
                was_updated = True

        self._output = combine(self.terminals)
        return was_updated

    def reset(self):
        self._output = "float"

    def validate(self):
        assert len(self.terminals) >= 2
        for term in self.terminals:
            assert term.net == self

    def __str__(self):
        return "<Net {}>".format(' '.join([str(t)[1:-1] for t in self.terminals]))


import sys

import logic


def main():

    if len(sys.argv) == 1:
        filename = None
        schematic = logic.Schematic()
    elif len(sys.argv) == 2:
        filename = sys.argv[1]
        schematic = logic.Schematic.from_file(filename)
    else:
        raise ValueError("Too many arguments")

    interface = logic.Interface(schematic, filename)
    interface.run()

if __name__ == "__main__":
    main()

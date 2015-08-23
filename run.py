
import sys

import logic


def main():

    if len(sys.argv) == 1:
        schematic = logic.Schematic()
    elif len(sys.argv) == 2:
        schematic = logic.Schematic.from_file(sys.argv[1])
    else:
        raise ValueError("Too many arguments")

    interface = logic.Interface(schematic)
    interface.run()

if __name__ == "__main__":
    main()

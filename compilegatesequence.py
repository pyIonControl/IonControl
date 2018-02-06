import argparse
from pathlib import Path

from gateSequence.GateDefinition import GateDefinition
from gateSequence.GateSequenceContainer import GateSequenceContainer
from modules.timing import timing

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compile gate sequence into pickle format')
    parser.add_argument('filename', type=str, default=None, help='filename of text or xml file to compile')
    args = parser.parse_args()

    c = GateSequenceContainer()
    with timing("load original"):
        c.loadText(args.filename)
    pkl_file = Path(args.filename).with_suffix(".pkl")
    with timing("save pickle"):
        c.savePickle(str(pkl_file))
    with timing("load pickle"):
        c.loadPickle(str(pkl_file))





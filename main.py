import argparse
import sys
from settings import APP_NAME, APP_DESCR
from koala_main import (
    koala_start,
    print_results_pretty,
)
from my_koala_writer_app import MyKoalaWriterApp

def main():
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=APP_DESCR,
        add_help=True
    )

    parser.add_argument(
        "-n", "--notion",
        help="Notion page URL(s) to process",
        type=str,
        nargs='+'
    )

    # If no arguments, launch the GUI
    if len(sys.argv) == 1:
        import tkinter as tk
        root = tk.Tk()
        app = MyKoalaWriterApp(root)
        root.mainloop()
        sys.exit(0)

    args = parser.parse_args()

    # Handle --notion argument
    if args.notion:
        print_results_pretty(koala_start(args.notion))


if __name__ == "__main__":
    main()

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
    parser.add_argument(
        "-t", "--test",
        help="Run in test mode",
        action="store_true"
    )

    # detect test flag early so the GUI can receive it before args are parsed
    test_mode = ("-t" in sys.argv) or ("--test" in sys.argv)
    if len(sys.argv) == 1 or len(sys.argv) == 2 and test_mode:
        import tkinter as tk
        root = tk.Tk()
        app = MyKoalaWriterApp(root, test_mode=test_mode)
        root.mainloop()
        sys.exit(0)

    args = parser.parse_args()

    # Handle --notion argument
    if args.notion:
        print_results_pretty(koala_start(args.notion))


if __name__ == "__main__":
    main()

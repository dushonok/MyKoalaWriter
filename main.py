import argparse
import sys
from settings import PROG_NAME, PROG_DESCRIPTION
from koala_main import koala_start

def main():
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description=PROG_DESCRIPTION,
        add_help=True
    )

    parser.add_argument(
        "-n", "--notion",
        help="Notion page URL to process",
        type=str
    )

    # ✅ If no arguments, show help (same as -h/--help)
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Handle --notion argument
    if args.notion:
        notion_url = args.notion
        koala_start(notion_url)


if __name__ == "__main__":
    main()

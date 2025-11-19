import argparse
import sys
from settings import APP_NAME, APP_DESCR
from koala_main import (
    write_post,
    print_results_pretty,
)
from my_koala_writer_app import MyKoalaWriterApp
from post_writer import PostWriter

def test_post_writer(notion_urls: list, test_mode: bool = False):
    """
    Test PostWriter.write_post() with a list of Notion URLs.
    Outputs results to console.
    
    Args:
        notion_urls: List of Notion page URLs to test
        test_mode: Whether to run in test mode (no AI calls)
    """
    print("\n" + "=" * 80)
    print(f"Testing PostWriter with {len(notion_urls)} URL(s)")
    print(f"Test Mode: {'ENABLED (no AI calls)' if test_mode else 'DISABLED (real AI calls)'}")
    print("=" * 80 + "\n")
    
    post_writer = PostWriter(test=test_mode, callback=print)
    
    for idx, notion_url in enumerate(notion_urls, 1):
        print(f"\n{'─' * 80}")
        print(f"Test {idx}/{len(notion_urls)}: {notion_url}")
        print(f"{'─' * 80}\n")
        
        try:
            # Set up test data (in real scenario, this would come from Notion)
            post_writer.post_title = f"Test Post {idx}"
            post_writer.post_topic = "recipes"  # Default topic for testing
            post_writer.post_type = "single"    # Default type for testing
            post_writer.notion_url = notion_url
            
            print(f"📝 Post Title: {post_writer.post_title}")
            print(f"📂 Post Topic: {post_writer.post_topic}")
            print(f"🔖 Post Type: {post_writer.post_type}")
            print(f"🔗 Notion URL: {notion_url}\n")
            
            # Call write_post
            title, body = post_writer.write_post()
            
            # Display results
            print(f"\n{'─' * 80}")
            print("✅ RESULTS:")
            print(f"{'─' * 80}")
            print(f"\n📌 Generated Title:\n{title}\n")
            print(f"📄 Generated Body (first 500 chars):")
            print(f"{body[:500]}...")
            print(f"\n📊 Body Length: {len(body)} characters")
            print(f"{'─' * 80}\n")
            
        except Exception as e:
            print(f"\n❌ ERROR testing URL {notion_url}:")
            print(f"   {type(e).__name__}: {str(e)}\n")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Testing Complete")
    print("=" * 80 + "\n")

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
        help="Run in test mode (no AI calls, returns mock data)",
        action="store_true"
    )
    parser.add_argument(
        "--test-writer",
        help="Test PostWriter.write_post() with Notion URL(s) and output results to console. Use with -t/--test to avoid AI calls.",
        type=str,
        nargs='+',
        metavar='URL'
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

    # Handle --test-writer argument
    if args.test_writer:
        test_post_writer(args.test_writer, test_mode=args.test)
        sys.exit(0)

    # Handle --notion argument
    if args.notion:
        print_results_pretty(write_post(args.notion))


if __name__ == "__main__":
    main()

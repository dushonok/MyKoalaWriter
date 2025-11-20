import argparse
import sys
from settings import APP_NAME, APP_DESCR
from koala_main import (
    write_post,
    print_results_pretty,
)
from my_koala_writer_app import MyKoalaWriterApp
from post_writer import PostWriter

def test_split_into_paragraphs():
    """Test the PostWriter._split_into_paragraphs method."""
    print("\n" + "=" * 80)
    print("Testing PostWriter._split_into_paragraphs()")
    print("=" * 80 + "\n")
    
    post_writer = PostWriter(test=True)
    
    test_cases = [
        {
            "name": "Simple 4-sentence text",
            "input": "This is the first sentence. This is the second sentence. This is the third sentence. This is the fourth sentence.",
            "sentences_per_paragraph": 2,
            "expected_paragraphs": 2
        },
        {
            "name": "Mixed punctuation",
            "input": "What is this? It's a question! Now a statement. And another one.",
            "sentences_per_paragraph": 2,
            "expected_paragraphs": 2
        },
        {
            "name": "Single paragraph (3 sentences)",
            "input": "First sentence here. Second sentence follows. Third one too.",
            "sentences_per_paragraph": 3,
            "expected_paragraphs": 1
        },
        {
            "name": "Empty text",
            "input": "",
            "sentences_per_paragraph": 2,
            "expected_paragraphs": 0
        },
        {
            "name": "Real recipe description",
            "input": "Baked salmon is a healthy and delicious option for dinner. It's packed with omega-3 fatty acids and protein. This recipe uses a simple lemon-herb marinade. The salmon comes out perfectly flaky and tender. Serve it with your favorite vegetables for a complete meal.",
            "sentences_per_paragraph": 2,
            "expected_paragraphs": 3
        }
    ]
    
    all_passed = True
    truncated_input = 200
    for idx, test_case in enumerate(test_cases, 1):
        print(f"Test {idx}: {test_case['name']}")
        print(f"{'─' * 80}")
        print(f"Input: {test_case['input'][:truncated_input]}{'...' if len(test_case['input']) > truncated_input else ''}")
        print(f"Sentences per paragraph: {test_case['sentences_per_paragraph']}\n")
        
        result = post_writer._split_into_paragraphs(
            test_case['input'],
            sentences_per_paragraph=test_case['sentences_per_paragraph']
        )
        
        paragraphs = result.split('\n') if result else []
        actual_count = len([p for p in paragraphs if p.strip()])
        expected_count = test_case['expected_paragraphs']
        
        # Check for empty lines (should not exist at all)
        has_empty_lines = '\n\n' in result or result.startswith('\n') or result.endswith('\n')
        
        passed = actual_count == expected_count and not has_empty_lines
        all_passed = all_passed and passed
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}")
        print(f"Expected paragraphs: {expected_count}")
        print(f"Actual paragraphs: {actual_count}")
        if has_empty_lines:
            print(f"⚠️  WARNING: Empty lines detected in output!")
        print(f"\nOutput:\n{result}\n")
        print(f"{'─' * 80}\n")
    
    print("=" * 80)
    if all_passed:
        print("✅ All tests PASSED!")
    else:
        print("❌ Some tests FAILED!")
    print("=" * 80 + "\n")

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
            # Get real data from Notion
            from notion_api import (
                get_post_title_website_from_url,
                get_post_type,
                get_page_property,
            )
            from notion_config import POST_WP_CATEGORY_PROP, POST_SLUG_PROP
            from config_utils import get_post_topic_by_cat
            
            post, post_title, website = get_post_title_website_from_url(notion_url)
            if post is None:
                raise ValueError(f"Could not resolve Notion URL: {notion_url}")
            if website is None:
                raise ValueError(f"Could not determine website! Did you forget to apply a Notion template?")
            
            post_writer.post_title = post_title
            post_writer.post_type = get_post_type(post)
            
            categories = get_page_property(post, POST_WP_CATEGORY_PROP)
            post_writer.post_topic = get_post_topic_by_cat(post)
            
            post_writer.notion_url = notion_url
            post_slug = get_page_property(post, POST_SLUG_PROP)
            
            print(f"🌐 Website: {website}")
            print(f"📝 Post Title: {post_writer.post_title}")
            print(f"📂 Post Topic: {post_writer.post_topic}")
            print(f"🔖 Post Type: {post_writer.post_type}")
            print(f"🔗 Post Slug: {post_slug}")
            print(f"📁 Categories: {categories}")
            print(f"🔗 Notion URL: {notion_url}\n")
            
            # Call write_post
            title, body = post_writer.write_post()
            
            # Display results
            body_len = 1000
            print(f"\n{'─' * 80}")
            print("✅ RESULTS:")
            print(f"{'─' * 80}")
            print(f"\n📌 Generated Title:\n{title}\n")
            print(f"📄 Generated Body (first {body_len} chars):")
            print(f"{body[:body_len]}...")
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
        "--test-writer", "-tw",
        help="Test PostWriter.write_post() with Notion URL(s) and output results to console. Use with -t/--test to avoid AI calls.",
        type=str,
        nargs='+',
        metavar='URL'
    )
    parser.add_argument(
        "--test-split", "-ts",
        help="Test PostWriter._split_into_paragraphs() method with various test cases",
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

    # Handle --test-split argument
    if args.test_split:
        test_split_into_paragraphs()
        sys.exit(0)

    # Handle --test-writer argument
    if args.test_writer:
        test_post_writer(args.test_writer, test_mode=args.test)
        sys.exit(0)

    # Handle --notion argument
    if args.notion:
        print_results_pretty(write_post(args.notion))


if __name__ == "__main__":
    main()

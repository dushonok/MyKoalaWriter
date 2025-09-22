import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))


from settings import *
from notion_api import (
    get_post_title_website_from_url,
    get_post_type,
    get_page_property,
    update_post_status,
)
from notion_config import (
    POST_WP_CATEGORY_PROP,
    POST_SLUG_PROP,
    POST_POST_STATUS_SETTING_UP_ID,
    POST_POST_STATUS_DRAFT_GENERATED_ID,
    POST_POST_STATUS_PUBLISHED_ID,
)
from ai_txt_gen import *
from wp_post_gen import *
from gen_utils import report_progress

def koala_start(notion_urls: list, callback=print):
    results = []
    url_count = len(notion_urls)
    report_progress(-1, url_count, callback)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\nStarting writing text for Notion URL: {notion_url}")

        post, title, website = get_post_title_website_from_url(notion_url)
        if website is None:
            raise ValueError(f"[ERROR][koala_start] Could not determine website! Did you forget to apply the Notion template?")
        post_type = get_post_type(post)
        categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        koala_post_type = KOALA_POST_TYPE_RECIPE
        post_slug = get_page_property(post, POST_SLUG_PROP)
        callback(f"\n\n[INFO][koala_start] Title: {title}")
        callback(f"[INFO][koala_start] Website: {website}")
        callback(f"[INFO][koala_start] Type: {post_type}")
        callback(f"[INFO][koala_start] Categories: {categories}")
        callback(f"[INFO][koala_start] Koala post type: {koala_post_type}")
        callback(f"[INFO][koala_start] Post slug: {post_slug}\n")

        post = update_post_status(post, POST_POST_STATUS_SETTING_UP_ID)
        if post is None:
            raise ValueError(f"[ERROR][koala_start] Post status #1 was not updated!")
        
        post_title, post_txt = write_post(title, koala_post_type, test=False, callback=callback)

        # Diabling this for now until it stabilizes
        # search_res = send_web_search_prompt_to_openai(f"Find 5 youtube videos that are related to '{title}' - verify they are real and if not, redo the search. If needed, broaden the search as much as needed to find less relevant matches. Only output the URLs and nothing else and if you cannot find any, output the word 'nothing'", test=False)
        # callback(f"\n[AI Response] Web search results:\n{search_res}\n")
        
        post = update_post_status(post, POST_POST_STATUS_DRAFT_GENERATED_ID)
        if post is None:
            raise ValueError(f"[ERROR][koala_start] Post status #2 was not updated!")
            
        wp_post = create_wp_post(
            notion_post=post,
            website=website,
            post_title=post_title,
            post_content=post_txt,
            post_slug=post_slug,
            categories=categories,
            callback=callback,
            test=False
        )

        wp_link = wp_post.get('link')
        if wp_link is None:
            raise ValueError(f"[ERROR][koala_start] WordPress post was not created!")
        callback(f"\n[INFO][koala_start] Post created on WordPress: {wp_link}\n")

        post = update_post_status(post, POST_POST_STATUS_PUBLISHED_ID)
        if post is None:
            raise ValueError(f"[ERROR][koala_start] Post status #3 was not updated!")

        results.append({f"{title}": f"{wp_link}"})

        report_progress(idx, url_count, callback)
    return results

def print_results_pretty(results):
    print("\n=== Koala Writer Results ===")
    for idx, result in enumerate(results, 1):
        for title, link in result.items():
            print(f"{idx}. {title}\n   → {link}")
    print("============================\n")
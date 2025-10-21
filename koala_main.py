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
from gen_utils import (
    report_progress,
    dedup_and_trim,
)
from config_utils import (
    get_post_topic_by_cat,
)
from checks import *

def koala_start(notion_urls: list, test=False, callback=print):
    if test:
        callback(f"\n[INFO][koala_start] Running in TEST mode!\n")

    results = []
    url_count = len(notion_urls)
    report_progress(-1, url_count, callback)

    notion_urls = dedup_and_trim(notion_urls)

    problems = run_checks(notion_urls, callback=callback)
    callback(format_check_res(problems))
    if len(problems) > 0:
        callback(f"\n\n[ERROR][koala_start] Cannot proceed due to the issues found ☝️")
        return results

    post_writer = PostWriter(test=test, callback=callback)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\nStarting writing text for Notion URL: {notion_url}")

        post, post_writer.post_title, website = get_post_title_website_from_url(notion_url)
        if post is None:
            raise ValueError(f"[ERROR][koala_start] Could not resolve Notion URL: {notion_url}")
        if website is None:
            raise ValueError(f"[ERROR][koala_start] Could not determine website! Did you forget to apply the Notion template?")
        
        post_type = get_post_type(post)
        categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        post_writer.post_topic = get_post_topic_by_cat(categories)
        post_slug = get_page_property(post, POST_SLUG_PROP)

        callback(f"\n\n[INFO][koala_start] WEBSITE: {website}")
        callback(f"[INFO][koala_start] Title: {post_writer.post_title}")
        callback(f"[INFO][koala_start] Type: {post_type}")
        callback(f"[INFO][koala_start] Categories: {categories}")
        callback(f"[INFO][koala_start] Post topic: {post_topic}")
        callback(f"[INFO][koala_start] Post slug: {post_slug}\n")

        post = update_post_status(post, POST_POST_STATUS_SETTING_UP_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][koala_start] Post status #1 was not updated!")
        
        post_title, post_txt = post_writer.write_post()

        # Diabling this for now until it stabilizes
        # search_res = send_web_search_prompt_to_openai(f"Find 5 youtube videos that are related to '{title}' - verify they are real and if not, redo the search. If needed, broaden the search as much as needed to find less relevant matches. Only output the URLs and nothing else and if you cannot find any, output the word 'nothing'", test=False)
        # callback(f"\n[AI Response] Web search results:\n{search_res}\n")
        
        post = update_post_status(post, POST_POST_STATUS_DRAFT_GENERATED_ID, test=test)
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
            test=test
        )

        wp_link = wp_post.get('link')
        if wp_link is None:
            raise ValueError(f"[ERROR][koala_start] WordPress post was not created!")
        callback(f"\n[INFO][koala_start] Post created on WordPress: {wp_link}\n")

        post = update_post_status(post, POST_POST_STATUS_PUBLISHED_ID, test=test)
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
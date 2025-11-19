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
from post_writer import *
from wp_post_gen import *
from gen_utils import (
    report_progress,
    reset_report_progress,
    dedup_and_trim,
)
from config_utils import (
    get_post_topic_by_cat,
)
from checks import *
from update_wp_content import (
    add_images_to_wp_post,
)

def write_post(notion_urls: list, test=False, callback=print):
    if test:
        callback(f"\n[INFO][write_post] Running in TEST mode!\n")

    results = []
    url_count = len(notion_urls)
    reset_report_progress(url_count, callback)

    notion_urls = dedup_and_trim(notion_urls)

    problems = run_checks(notion_urls, callback=callback)
    callback(format_check_res(problems))
    if len(problems) > 0:
        callback(f"\n\n[ERROR][write_post] Cannot proceed due to the issues found ☝️")
        return results

    post_writer = PostWriter(test=test, callback=callback)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\nStarting writing text for Notion URL: {notion_url}")

        post, post_writer.post_title, website = get_post_title_website_from_url(notion_url)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Could not resolve Notion URL: {notion_url}")
        if website is None:
            raise ValueError(f"[ERROR][write_post] Could not determine website! Did you forget to apply the Notion template?")
        
        callback(f"\n\n[INFO][write_post] WEBSITE: {website}")
        callback(f"[INFO][write_post] Title: {post_writer.post_title}")
        
        post_writer.post_type = get_post_type(post)
        callback(f"[INFO][write_post] Type: {post_type}")
        
        categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        callback(f"[INFO][write_post] Categories: {categories}")
        
        post_writer.post_topic = get_post_topic_from_cats(categories)
        callback(f"[INFO][write_post] Post topic: {post_writer.post_topic}")
        
        post_slug = get_page_property(post, POST_SLUG_PROP)
        callback(f"[INFO][write_post] Post slug: {post_slug}\n")

        post = update_post_status(post, POST_POST_STATUS_SETTING_UP_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Post status #1 was not updated!")
        
        post_title, post_txt = post_writer.write_post()

        # Diabling this for now until it stabilizes
        # search_res = send_web_search_prompt_to_openai(f"Find 5 youtube videos that are related to '{title}' - verify they are real and if not, redo the search. If needed, broaden the search as much as needed to find less relevant matches. Only output the URLs and nothing else and if you cannot find any, output the word 'nothing'", test=False)
        # callback(f"\n[AI Response] Web search results:\n{search_res}\n")
        
        post = update_post_status(post, POST_POST_STATUS_DRAFT_GENERATED_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Post status #2 was not updated!")
            
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
            raise ValueError(f"[ERROR][write_post] WordPress post was not created!")
        callback(f"\n[INFO][write_post] Post created on WordPress: {wp_link}\n")

        post = update_post_status(post, POST_POST_STATUS_PUBLISHED_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Post status #3 was not updated!")

        results.append({f"{post_title}": f"{wp_link}"})

        report_progress(idx, url_count, callback)
    return results

def print_results_pretty(results):
    print("\n=== Koala Writer Results ===")
    for idx, result in enumerate(results, 1):
        for title, link in result.items():
            print(f"{idx}. {title}\n   → {link}")
    print("============================\n")

def add_wp_imgs(notion_urls: list, test=False, callback=print):
    test = True  # Force test mode for now
    if test:
        callback(f"\n[INFO][add_wp_img] Running in TEST mode!\n")

    #TODO: Add checks: WP posts exist, images exist in folders, etc.

    results = []
    url_count = len(notion_urls)
    reset_report_progress(url_count, callback)

    notion_urls = dedup_and_trim(notion_urls)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\nStarting adding images to the WP post for Notion URL: {notion_url}")

        post, post_title, website = get_post_title_website_from_url(notion_url)
        if post is None:
            raise ValueError(f"[ERROR][add_wp_img] Could not resolve Notion URL: {notion_url}")
        if website is None:
            raise ValueError(f"[ERROR][add_wp_img] Could not determine website! Did you forget to apply the Notion template?")
        
        callback(f"\n\n[INFO][add_wp_img] WEBSITE: {website}")
        callback(f"[INFO][add_wp_img] Title: {post_title}\n")

        wp_link = add_images_to_wp_post(
            notion_post=post,
            website=website,
            post_title=post_title,
            callback=callback,
            test=test
        )
        
        callback(f"\n[INFO][add_wp_img] Post updated on WordPress with images: {wp_link}\n")

        results.append({f"{post_title}": f"{wp_link}"})
        report_progress(idx, url_count, callback)

    return results
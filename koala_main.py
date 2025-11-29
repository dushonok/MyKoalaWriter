import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))


from settings import *
from notion_api import (
    get_post_title_website_from_url,
    get_post_type,
    get_page_property,
    update_post_status,
    update_post_ai_img_prompt,
)
from notion_config import (
    POST_WP_CATEGORY_PROP,
    POST_SLUG_PROP,
    POST_POST_STATUS_SETTING_UP_ID,
    POST_POST_STATUS_DRAFT_GENERATED_ID,
    POST_POST_STATUS_PUBLISHED_ID,
    POST_POST_URL_PROP,
    POST_AI_IMAGE_PROMPT_PROP,
    POST_TYPES_CONFIG,
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
from ai_gen_config import POST_TOPIC_RECIPES
from checks import *
from update_wp_content import (
    add_images_to_wp_post,
)
from wp_formatter import WPFormatter
from post_part_constants import *

def write_post(notion_urls: list, test=False, callback=print):
    if test:
        callback(f"\n[INFO][write_post] Running in TEST mode!\n")

    notion_urls = dedup_and_trim(notion_urls)
    url_count = len(notion_urls)
    reset_report_progress(url_count, callback)

    results = []
    problems = run_checks(notion_urls, callback=callback)
    callback(format_check_res(problems))
    if len(problems) > 0:
        callback(f"\n\n[ERROR][write_post] Cannot proceed due to the issues found ☝️")
        return results

    post_writer = PostWriter(test=test, callback=callback)

    for idx, post_writer.notion_url in enumerate(notion_urls):
        
        callback(f"\nStarting writing text for Notion URL: {post_writer.notion_url}")

        post, post_writer.post_title, website = get_post_title_website_from_url(post_writer.notion_url)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Could not resolve Notion URL: {post_writer.notion_url}")
        if website is None:
            raise ValueError(f"[ERROR][write_post] Could not determine website! Did you forget to apply the Notion template?")
        
        callback(f"\n\n[INFO][write_post] WEBSITE: {website}")
        callback(f"[INFO][write_post] Title: {post_writer.post_title}")
        
        post_writer.post_type = get_post_type(post)
        callback(f"[INFO][write_post] Type: {post_writer.post_type}")
        
        categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        callback(f"[INFO][write_post] Categories: {categories}")
        
        post_writer.post_topic = get_post_topic_from_cats(categories)
        callback(f"[INFO][write_post] Post topic: {post_writer.post_topic}")
        
        post_slug = get_page_property(post, POST_SLUG_PROP)
        callback(f"[INFO][write_post] Post slug: {post_slug}\n")

        post = update_post_status(post, POST_POST_STATUS_SETTING_UP_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Post status #1 was not updated!")
        
        post_parts = post_writer.write_post()

        # Diabling this for now until it stabilizes
        # search_res = send_web_search_prompt_to_openai(f"Find 5 youtube videos that are related to '{title}' - verify they are real and if not, redo the search. If needed, broaden the search as much as needed to find less relevant matches. Only output the URLs and nothing else and if you cannot find any, output the word 'nothing'", test=False)
        # callback(f"\n[AI Response] Web search results:\n{search_res}\n")

        _update_page_ai_img_prompt(post, post_parts.get(POST_PART_INGREDIENTS, ""), test=test, callback=callback)
        
        post = update_post_status(post, POST_POST_STATUS_DRAFT_GENERATED_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Post status #2 was not updated!")
            
        wp_post = create_wp_post(
            notion_post=post,
            website=website,
            post_parts=post_parts,
            post_slug=post_slug,
            categories=categories,
            callback=callback,
            test=test
        )

        wp_link = wp_post.get('link')
        if wp_link is None:
            raise ValueError(f"[ERROR][write_post] WordPress post was not created!")
        callback(f"\n[INFO][write_post] Post created on WordPress: {wp_link}\n")

        #TODO: Based on the slug in wp_post, update the Notion title accordingly - it may have a number at the end

        post = update_post_status(post, POST_POST_STATUS_PUBLISHED_ID, test=test)
        if post is None:
            raise ValueError(f"[ERROR][write_post] Post status #3 was not updated!")

        # Extract title from post_parts for results
        final_title = post_parts.get(POST_PART_TITLE, post_writer.post_title)
        results.append({f"{final_title}": f"{wp_link}"})

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

    #TODO: Add checks: WP posts exist, images exist in folders, post images exist for roundups, etc.

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

def _update_page_ai_img_prompt(notion_post, new_prompt: str, test=False, callback=print):
    """Update the AI Image Prompt property of a Notion page."""
    callback(f"\n[INFO][_update_page_ai_img_prompt] Updating '{POST_AI_IMAGE_PROMPT_PROP}' property...")

    if isinstance(new_prompt, list):
        new_prompt = " ".join(new_prompt)

    if new_prompt.strip() == "":
        callback(f"[WARNING][_update_page_ai_img_prompt] New prompt is empty, skipping update.")
        return None
    
    if test:
        callback(f"[TEST][_update_page_ai_img_prompt] No update is made. Would set to: {new_prompt}")
    else:
        updated_post = update_post_ai_img_prompt(notion_post, new_prompt)
        if updated_post is None:
            raise ValueError(f"[ERROR][_update_page_ai_img_prompt] Failed to update '{POST_AI_IMAGE_PROMPT_PROP}' property!")
    callback(f"[INFO][_update_page_ai_img_prompt] '{POST_AI_IMAGE_PROMPT_PROP}' updated successfully.")
    return updated_post
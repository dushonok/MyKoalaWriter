
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'WordPress')))

from typing import List, Dict

# Use helper utilities from the project (these should be available in the project path)
from gen_utils import (
    report_progress,
    dedup_and_trim,
    reset_report_progress,
)
from config_utils import (
    get_post_topic_from_cats,
    load_generic_input_folder,
    get_post_folder,
    get_ims_in_folder,
)
from notion_api import (
    get_post_title_website_from_url,
    get_post_type,
    get_page_property,
    get_post_images_for_blog_url,
    get_post_title,
)
from notion_config import (
    POST_WP_CATEGORY_PROP,
    POST_POST_STATUS_PROP,
    POST_PINTEREST_STATUS_PROP,
    POST_POST_TYPE_SINGLE_ITEM_ID,
    POST_POST_TYPE_ROUNDUP_ID,
    POST_POST_TYPE_ID_TO_NAME,
    POST_POST_STATUS_NOT_STARTED_ID,
    POST_PINTEREST_STATUS_NOT_STARTED_ID,
    POST_PINTEREST_STATUS_RESEARCH_ID,
    PostStatuses,
    POST_PINTEREST_STATUS_ID_TO_NAME,
)
from ai_gen_config import (
    POST_TOPIC_RECIPES,
    POST_TOPIC_OUTFITS,
    POST_TOPIC_AI_PROMPT_NOUNS,
)
from wp_client import WordPressClient
from post_writer import PostWriter

MY_KOALA_POST_STATUSES_ALLOWED = [
    PostStatuses.not_started_id,
    PostStatuses.setting_up_id,
    PostStatuses.imgs_downloaded_id,
]

MY_KOALA_POST_TYPES_ALLOWED = {
    POST_TOPIC_RECIPES: [POST_POST_TYPE_SINGLE_ITEM_ID, POST_POST_TYPE_ROUNDUP_ID],
    POST_TOPIC_OUTFITS: [POST_POST_TYPE_SINGLE_ITEM_ID, POST_POST_TYPE_ROUNDUP_ID],
}

def _resolve_notion_url(notion_url: str, idx: int, url_count: int, results: List[Dict], callback=print):
    """Resolve a Notion URL and handle early-exit errors.
    
    Returns:
        tuple: (post, title, website) if successful, (None, None, None) if error occurred
    """
    try:
        post, title, website = get_post_title_website_from_url(notion_url)
    except Exception as e:
        results.append({
            "url": notion_url,
            "title": None,
            "website": None,
            "issues": [f"Exception resolving URL: {e}"],
        })
        report_progress(idx, url_count, callback)
        return None, None, None

    if website is None:
        results.append({
            "url": notion_url,
            "title": title,
            "website": None,
            "issues": ["Could not determine website (Page is missing Notion template?)"],
        })
        report_progress(idx, url_count, callback)
        return None, None, None
    
    return post, title, website

def _test_wp_connection(website: str, tested_websites: Dict[str, bool], issues: List[str], callback=print):
    """Test WordPress connection for a website and cache the result.
    
    Args:
        website: Website identifier
        tested_websites: Dictionary caching connection test results by website
        issues: List to append connection failure message to
        callback: Logging callback
    """
    if website not in tested_websites:
        wp_connection_test = WordPressClient(website, callback).test_connection()
        tested_websites[website] = wp_connection_test
    else:
        wp_connection_test = tested_websites[website]
    
    if not wp_connection_test:
        issues.append("Could not connect to WordPress site with provided credentials")

def _validate_post_title(post, issues: List[str]):
    """Validate post title and append issues if invalid.
    
    Args:
        post: Notion post object
        issues: List to append validation errors to
    
    Returns:
        str: The post title (empty string if invalid)
    """
    post_title = ""
    try:
        post_title = get_post_title(post)
        if not post_title:
            issues.append("Post title is empty")
    except Exception as e:
        issues.append(f"Exception while retrieving post title: {e}")
    return post_title

def _validate_categories_and_topic(post, issues: List[str], callback=print):
    """Validate categories and derive post topic.
    
    Args:
        post: Notion post object
        issues: List to append validation errors to
        callback: Logging callback
    
    Returns:
        tuple: (categories, post_topic) - both may be empty strings if invalid
    """
    post_topic = ""
    categories = None
    
    try:
        categories = get_page_property(post, POST_WP_CATEGORY_PROP)
    except Exception as e:
        categories = None
        issues.append(f"Exception while reading WP categories: {e}")
    
    if categories in (None, [], ""):
        issues.append("No WP categories assigned")
    else:
        try:
            post_topic = get_post_topic_from_cats(categories=categories, callback=callback)
            if post_topic in (None, [], ""):
                issues.append("Post topic derived from categories is empty")
        except Exception as e:
            post_topic = ""
            issues.append(f"Exception determining post topic from categories: {e}")
    
    return categories, post_topic

def _validate_post_type(post, post_topic: str, issues: List[str]):
    """Validate post type against allowed types for the post topic.
    
    Args:
        post: Notion post object
        post_topic: The derived post topic
        issues: List to append validation errors to
    
    Returns:
        str or None: The post type if successfully retrieved, None otherwise
    """
    try:
        post_type = get_post_type(post)
    except Exception as e:
        post_type = None
        issues.append(f"Exception while reading post type: {e}")
    
    # Validate post_type only if we have a known post_topic mapping
    if post_topic in MY_KOALA_POST_TYPES_ALLOWED:
        allowed_for_topic = MY_KOALA_POST_TYPES_ALLOWED[post_topic]
        if post_type not in allowed_for_topic:
            expected_names = ", ".join([POST_POST_TYPE_ID_TO_NAME.get(t, str(t)) for t in allowed_for_topic])
            issues.append(f"Post type is unexpected: '{post_type}' (expecting one of: {expected_names})")
    else:
        issues.append(f"Unknown or unsupported post topic '{post_topic}'")
        issues.append(f"Post type is unexpected: '{post_type}' (expecting '{POST_POST_TYPE_ID_TO_NAME[POST_POST_TYPE_SINGLE_ITEM_ID]}')")
    
    return post_type

def _validate_post_status(post, allowed_statuses: List[str], issues: List[str]):
    """Validate post status against allowed statuses.
    
    Args:
        post: Notion post object
        allowed_statuses: List of allowed status IDs
        issues: List to append validation errors to
    
    Returns:
        str or None: The post status if successfully retrieved, None otherwise
    """
    post_status = None
    post_statuses = PostStatuses()
    try:
        post_status = get_post_status(post)
    except Exception as e:
        post_status = None
        issues.append(f"Exception while reading post status: {e}")
    
    if post_status not in allowed_statuses:
        status_txt = post_statuses.get_status_name(post_status)
        allowed_names = [post_statuses.get_status_name(s) for s in post_statuses.post_done_with_post_statuses]
        expected_str = " or ".join([f"'{name}'" for name in allowed_names])
        issues.append(f"Post status is unexpected: '{status_txt}' (expecting {expected_str})")

    return post_status

def run_checks(notion_urls: List[str], callback=print) -> List[Dict]:
    """
    Run a set of basic checks for each Notion URL and return a structured
    list of results. Each result is a dict with keys:
      - url
      - title
      - website
      - status: 'ok' | 'error' | 'warning'
      - issues: list of issue strings
    """
    results: List[Dict] = []
    tested_websites: Dict[str, bool] = {}  # Track WP connection test results by website

    notion_urls = dedup_and_trim(notion_urls, callback=callback)
    url_count = len(notion_urls)
    reset_report_progress(url_count, callback)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\n[INFO][run_checks] Starting checks for Notion URL: {notion_url}")

        post, title, website = _resolve_notion_url(notion_url, idx, url_count, results, callback)
        if post is None:
            continue

        issues = []

        _test_wp_connection(website, tested_websites, issues, callback)

        # Basic property reads and validations
        post_title = _validate_post_title(post, issues)

        categories, post_topic = _validate_categories_and_topic(post, issues, callback)
        
        post_type = _validate_post_type(post, post_topic, issues)
        
        post_status = _validate_post_status(post, MY_KOALA_POST_STATUSES_ALLOWED, issues)

        if post_type == POST_POST_TYPE_ROUNDUP_ID:
            try:
                # TODO: Return roundup items to use for the post creation to speed up the process
                roundup_items = get_post_images_for_blog_url(notion_url)
                if not roundup_items or len(roundup_items) == 0:
                    issues.append("No roundup items found for roundup post")
            except Exception as e:
                roundup_items = None
                issues.append(f"Exception while reading roundup items: {e}")
                
        prompts = PostWriter.AI_TXT_GEN_PROMPTS_BY_TOPIC.get(post_topic, {})
        if prompts is None:
            issues.append(f"No AI_TXT_GEN_PROMPTS_BY_TOPIC prompt found for post topic '{post_topic}' and prompt type '{prompt_type}'")

        if post_topic not in POST_TOPIC_AI_PROMPT_NOUNS:
            issues.append(f"No AI prompt nouns defined for post topic '{post_topic}'")


        if issues:
            result = {
                "url": notion_url,
                "title": title,
                "website": website,
                "issues": issues,
                "meta": {
                    "post_type": post_type,
                    "categories": categories,
                    "post_status": post_status,
                    "post_pinterest_status": ""
                },
            }
            results.append(result)

        report_progress(idx, url_count, callback)

    return results

def run_wp_img_add_checks(notion_post: Dict, callback=print) -> List[Dict]:
    """
    Run checks specific to adding images to WordPress posts.
    Returns a list of issues found.
    """
    """
    Run a set of basic checks for each Notion URL and return a structured
    list of results. Each result is a dict with keys:
      - url
      - title
      - website
      - status: 'ok' | 'error' | 'warning'
      - issues: list of issue strings
    """
    results: List[Dict] = []
    tested_websites: Dict[str, bool] = {}  # Track WP connection test results by website

    notion_urls = dedup_and_trim(notion_urls, callback=callback)
    url_count = len(notion_urls)
    reset_report_progress(url_count, callback)
    generic_input_folder = load_generic_input_folder()

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\n[INFO][run_checks] Starting checks for Notion URL: {notion_url}")

        post, title, website = _resolve_notion_url(notion_url, idx, url_count, results, callback)
        if post is None:
            continue

        issues = []

        _test_wp_connection(website, tested_websites, issues, callback)

        # Basic property reads and validations
        post_title = _validate_post_title(post, issues)

        slug = ""
        try:
            slug = get_post_slug(notion_post)
        except Exception as e:
            slug = None
            issues.append(f"Exception while retreiving post slug: {e}")

        categories, post_topic = _validate_categories_and_topic(post, issues, callback)
        
        post_type = _validate_post_type(post, post_topic, issues)
        
        post_status = _validate_post_status(post, post_statuses.post_done_with_post_statuses, issues)

        is_recipes_roundup = post_topic == POST_TOPIC_RECIPES and is_roundup
        try:
            post_folder = get_post_folder(generic_input_folder, post, for_pins=not is_recipes_roundup)
            imgs = get_ims_in_folder(post_folder, doSort=False)
            if not imgs or len(imgs) == 0:
                issues.append(f"No images found in post folder '{post_folder}' for adding to WordPress")
        except Exception as e:
            imgs = None
            issues.append(f"Exception while retrieving images from post folder: {e}")

        if issues:
            result = {
                "url": notion_url,
                "title": title,
                "website": website,
                "issues": issues,
                "meta": {
                    "post_type": post_type,
                    "categories": categories,
                    "post_status": post_status,
                    "post_pinterest_status": ""
                },
            }
            results.append(result)

        report_progress(idx, url_count, callback)

    return results


def format_check_res(check_res: List[Dict]) -> str:
    if not check_res or len(check_res) == 0:
        return "✅ All the checks passed!"

    lines = []
    for res in check_res:
        lines.append(f"URL: {res['url']}")
        lines.append(f"Title: {res['title']}")
        lines.append(f"Website: {res['website']}")
        if res['issues']:
            lines.append("Issues:")
            for issue in res['issues']:
                lines.append(f"  - {issue}")
        else:
            lines.append("Issues: None")
        lines.append("")  # Blank line between entries
    return "\n❌Checks failed! Issues found:\n\n" + "\n".join(lines) + "\n\nPlease fix before proceeding or run only for URLs that have no issues."
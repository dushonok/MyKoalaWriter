
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))

from typing import List, Dict

# Use helper utilities from the project (these should be available in the project path)
from gen_utils import (
    report_progress,
    dedup_and_trim,
    reset_report_progress,
)
from notion_api import (
    get_post_title_website_from_url,
    get_post_type,
    get_page_property,
)
from notion_config import (
    POST_WP_CATEGORY_PROP,
    POST_POST_STATUS_PROP,
    POST_PINTEREST_STATUS_PROP,
    POST_POST_TYPE_SINGLE_ITEM_ID,
    POST_POST_TYPE_ID_TO_NAME,
    POST_POST_STATUS_NOT_STARTED_ID,
    POST_PINTEREST_STATUS_NOT_STARTED_ID,
    POST_PINTEREST_STATUS_RESEARCH_ID,
    POST_POST_STATUS_SETTING_UP_ID,
    POST_POST_STATUS_ID_TO_NAME,
    POST_POST_STATUS_IMGS_DOWNLOADED_ID,
    POST_PINTEREST_STATUS_ID_TO_NAME,
)

MY_KOALA_POST_STATUSES_ALLOWED = [
    POST_POST_STATUS_NOT_STARTED_ID,
    POST_POST_STATUS_SETTING_UP_ID,
    POST_POST_STATUS_IMGS_DOWNLOADED_ID,
]

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

    notion_urls = dedup_and_trim(notion_urls, callback=callback)
    url_count = len(notion_urls)
    reset_report_progress(url_count, callback)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\n[INFO][run_checks] Starting checks for Notion URL: {notion_url}")

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
            continue

        if website is None:
            results.append({
                "url": notion_url,
                "title": title,
                "website": None,
                "issues": ["Could not determine website (Page is missing Notion template?)"],
            })
            report_progress(idx, url_count, callback)
            continue

        issues = []

        # Basic property reads
        try:
            post_type = get_post_type(post)
        except Exception:
            post_type = None
            issues.append("Could not read post type")
        if post_type != POST_POST_TYPE_SINGLE_ITEM_ID:
            issues.append(f"Post type is unexpected: '{post_type}' (expecting '{POST_POST_TYPE_ID_TO_NAME[POST_POST_TYPE_SINGLE_ITEM_ID]}')")
        
        try:
            categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        except Exception:
            categories = None
            issues.append("Could not read WP categories")
        if categories in (None, [], ""):
            issues.append("No WP categories assigned")

        try:
            post_status = get_page_property(post, POST_POST_STATUS_PROP)
        except Exception:
            post_status = None
            issues.append("Could not read post status")
        if post_status not in MY_KOALA_POST_STATUSES_ALLOWED:
            status_txt = POST_POST_STATUS_ID_TO_NAME.get(post_status, f"Unknown status for id '{post_status}'")
            allowed_names = [POST_POST_STATUS_ID_TO_NAME.get(s, f"Unknown status for id '{s}'") for s in MY_KOALA_POST_STATUSES_ALLOWED]
            expected_str = " or ".join([f"'{name}'" for name in allowed_names])
            issues.append(f"Post status is unexpected: '{status_txt}' (expecting {expected_str})")


        try:
            post_pinterest_status = get_page_property(post, POST_PINTEREST_STATUS_PROP)
        except Exception:
            post_pinterest_status = None
            issues.append("Could not read Pinterest status")
        if post_pinterest_status != POST_PINTEREST_STATUS_NOT_STARTED_ID and post_pinterest_status != POST_PINTEREST_STATUS_RESEARCH_ID:
            status = POST_PINTEREST_STATUS_ID_TO_NAME.get(post_pinterest_status, f"Unknown status for id '{post_pinterest_status}'")
            issues.append(f"Pinterest status is unexpected: '{status}' (expecting '{POST_PINTEREST_STATUS_ID_TO_NAME[POST_PINTEREST_STATUS_NOT_STARTED_ID]}' or '{POST_PINTEREST_STATUS_ID_TO_NAME[POST_PINTEREST_STATUS_RESEARCH_ID]}')")
        
    
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
                    "post_pinterest_status": post_pinterest_status,
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
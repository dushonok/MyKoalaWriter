
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionUtils')))

from typing import List, Dict

# Use helper utilities from the project (these should be available in the project path)
from gen_utils import report_progress
from gen_utils import dedup_and_trim
from notion_api import (
    get_post_title_website_from_url,
    get_post_type,
    get_page_property,
)
from notion_config import (
    POST_WP_CATEGORY_PROP,
    POST_POST_STATUS_PROP,
    POST_PINTEREST_STATUS_PROP,
)


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
    report_progress(-1, url_count, callback)

    for idx, notion_url in enumerate(notion_urls):
        callback(f"\n[INFO][run_checks] Starting checks for Notion URL: {notion_url}")

        try:
            post, title, website = get_post_title_website_from_url(notion_url)
        except Exception as e:
            callback(f"[ERROR][run_checks] Exception while resolving URL: {e}")
            results.append({
                "url": notion_url,
                "title": None,
                "website": None,
                "status": "error",
                "issues": [f"Exception resolving URL: {e}"],
            })
            report_progress(idx, url_count, callback)
            continue

        if website is None:
            callback(f"[ERROR][run_checks] Could not determine website for {notion_url}")
            results.append({
                "url": notion_url,
                "title": title,
                "website": None,
                "status": "error",
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

        try:
            categories = get_page_property(post, POST_WP_CATEGORY_PROP)
        except Exception:
            categories = None
            issues.append("Could not read WP categories")

        try:
            post_status = get_page_property(post, POST_POST_STATUS_PROP)
        except Exception:
            post_status = None
            issues.append("Could not read post status")

        try:
            post_pinterest_status = get_page_property(post, POST_PINTEREST_STATUS_PROP)
        except Exception:
            post_pinterest_status = None
            issues.append("Could not read Pinterest status")

        # Example checks (add or change per project needs)
        if post_type is None:
            issues.append("Missing post type")

        if categories in (None, [], ""):
            issues.append("No categories assigned")

        if post_status is None:
            issues.append("Post status not set")

        if post_pinterest_status is None:
            issues.append("Pinterest status not set")

        # Build result record
        status = "ok" if not issues else ("warning" if len(issues) < 2 else "error")

        result = {
            "url": notion_url,
            "title": title,
            "website": website,
            "status": status,
            "issues": issues,
            "meta": {
                "post_type": post_type,
                "categories": categories,
                "post_status": post_status,
                "post_pinterest_status": post_pinterest_status,
            },
        }

        if status == "ok":
            callback(f"[INFO][run_checks] All checks passed for '{title}'.")
        else:
            callback(f"[WARN][run_checks] Issues for '{title}': {issues}")

        results.append(result)
        report_progress(idx, url_count, callback)

    return results
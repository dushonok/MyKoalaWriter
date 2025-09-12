import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'NotionAutomator')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))


from settings import *
from notion_api import (
    get_post_title_website_from_url,
    get_post_type,
    get_page_property,
)
from notion_config import (
    POST_WP_CATEGORY_PROP,
)
from ai_txt_gen import *

def koala_start(notion_url: str, callback=print):
    print(f"\nStarting {PROG_NAME} with Notion URL: {notion_url}")

    post, title, website = get_post_title_website_from_url(notion_url)
    post_type = get_post_type(post)
    categories = get_page_property(post, POST_WP_CATEGORY_PROP)
    koala_post_type = KOALA_POST_TYPE_RECIPE
    callback(f"\n\n[INFO][koala_start] Title: {title}")
    callback(f"[INFO][koala_start] Website: {website}")
    callback(f"[INFO][koala_start] Type: {post_type}")
    callback(f"[INFO][koala_start] Categories: {categories}")
    callback(f"[INFO][koala_start] Koala post type: {koala_post_type}")

    # TODO: Change the Post Status on the Notion page to "Setting up"

    post_title, post_txt = write_post(title, koala_post_type, test=False, callback=callback)

    callback(f"\n[AI Response] Title:\n{post_title}\n")
    callback(f"\n[AI Response] Post:\n{post_txt}\n")

    #TODO: Change the Post Status on the Notion page to "Post draft being generated"
        
    #TODO: Create a WP post

    #TODO: Change the Post Status on the Notion page to "Published"
    
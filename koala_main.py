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
    POST_SLUG_PROP,
)
from ai_txt_gen import *
from wp_post_gen import *

def koala_start(notion_url: str, callback=print):
    print(f"\nStarting {PROG_NAME} with Notion URL: {notion_url}")

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

    # TODO: Change the Post Status on the Notion page to "Setting up"

    post_title, post_txt = write_post(title, koala_post_type, test=False, callback=callback)

    # We can remove this eventually
    # callback(f"\n[AI Response] Title:\n{post_title}\n")
    # callback(f"\n[AI Response] Post:\n{post_txt}\n")

    search_res = send_web_search_prompt_to_openai(f"Find 5 youtube videos for '{title}' - verify they are real and if not, redo the search. Output the URLs only even if you could not find the exact videos. If needed,  broaden the search as much as needed to find closer matches - but only output the URLs and nothing else and if you cannot find any, output the word 'nothing'", test=False)
    callback(f"\n[AI Response] Web search results:\n{search_res}\n")
    
    #TODO: Change the Post Status on the Notion page to "Post draft being generated"
        
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

    callback(f"\n[INFO][koala_start] Post created on WordPress: {wp_post.get('link')}\n")

    #TODO: Change the Post Status on the Notion page to "Published"
    
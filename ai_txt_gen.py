import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

import html
from chatgpt_api import *
from chatgpt_settings import *
from settings import *
from ai_txt_gen_settings import *

def write_post(post_title,koala_post_type, test = False, callback=print):
    if test:
        return f"{post_title} not modified", f"Test post about {post_title} of type {koala_post_type}"

    SYS_PROMPT_BASE = f"yOU ARE A PROFESSOINAL {koala_post_type} WRITER AND COPYWRITER. Your style is humorous, friendly, engaging, and informative. You write in a clear and concise manner, making complex topics easy to understand. You have a knack for storytelling and can weave narratives that captivate readers. Your tone is warm, approachable, and humorous, making readers feel like they are having a conversation with a knowledgeable friend who cracks family-friendly jokes all the time. You are also skilled at SEO writing, ensuring that your content is optimized for search engines while still being enjoyable to read."
    
    sys_prompt = SYS_PROMPT_BASE
    sys_prompt += AI_TXT_GEN_PROPMPTS_BY_TYPE[koala_post_type]["post"]

    user_prompt = f"Write a detailed {koala_post_type} blog post about '{post_title}'. Make sure to follow the structure and style guidelines provided. The post should be engaging, informative, and easy to read. Ensure the content is original and provides value to the readers."

    verbosity = CHATGPT_VERBOSITY_HIGH if koala_post_type == KOALA_POST_TYPE_RECIPE else CHATGPT_VERBOSITY_MEDIUM

    post_txt = send_prompt_to_openai(
        system_prompt = sys_prompt, 
        user_prompt = user_prompt, 
        response_format = "", 
        verbosity = verbosity,
        test = False)

    if post_txt["error"] != "":
        raise OpenAIAPIError(f"OpenAI API error: {post_txt['error']} '{post_txt['message']}'")
    
    sys_prompt = SYS_PROMPT_BASE
    sys_prompt += AI_TXT_GEN_PROPMPTS_BY_TYPE[koala_post_type]["title"]

    user_prompt = f"Generate a catchy and SEO-friendly blog post title for the following blog post about '{post_title}'. The title should be engaging and encourage readers to click on the article. It should also include relevant keywords that would help improve the post's search engine ranking.\nPost text:\n{post_txt['message']}"

    # "response_format" => [
    #         "type" => "json_schema",
    #         "json_schema" => [
    #             "name" => "recipe_description",
    #             "schema" => [
    #                 "type" => "object",
    #                 "properties" => [
    #                     "intro" => [ 
    #                         "type" => "string"
    #                     ],
    #                     "equipmen-must-have" => [
    #                         "type" => "array",
    #                         "items" => [
    #                             "type" => "string",
    #                             "additionalProperties" => false
    #                         ]
    #                     ],
    #                     "equipmen-nice-to-have" => [
    #                         "type" => "array",
    #                         "items" => [
    #                             "type" => "string",
    #                             "additionalProperties" => false
    #                         ]
    #                     ],
    #                     "ingredients" => [
    #                         "type" => "array",
    #                         "items" => [
    #                             "type" => "string",
    #                             "additionalProperties" => false
    #                         ]
    #                     ],
    #                     "instructions" => [
    #                         "type" => "array",
    #                         "items" => [
    #                             "type" => "string",
    #                             "additionalProperties" => false
    #                         ]
    #                     ],
    #                     "steps" => [
    #                         "type" => "array",
    #                         "items" => [
    #                             "type" => "string",
    #                             "additionalProperties" => false
    #                         ]
    #                     ]
    #                 ],
    #                 "required" => [
    #                     "title",
    #                     "alt",
    #                     "pin",
    #                     "story",
    #                     "steps intro",
    #                     "steps"
    #                 ],
    #                 "additionalProperties" => false
    #             ],
    #             "strict" => true
    #         ]
    #     ]

    post_title = send_prompt_to_openai(
        system_prompt = sys_prompt, 
        user_prompt = user_prompt, 
        response_format = "", 
        verbosity = CHATGPT_VERBOSITY_MEDIUM,
        test = False)

    if post_title["error"] != "":
        raise OpenAIAPIError(f"OpenAI API error: {post_title['error']} '{post_title['message']}'")
    
    txt = post_txt['message']
    txt = html.unescape(txt) if _is_escaped(txt) else txt

    title = post_title['message']
    return title, txt 

def _is_escaped(text: str) -> bool:
    return text != html.unescape(text)
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

import html
from chatgpt_api import *
from chatgpt_settings import *
from settings import *
from ai_txt_gen_settings import *

class PostWriter:
    AI_TXT_GEN_PROMPTS_BY_TOPIC = {
        POST_TOPIC_RECIPES: {
            "title": AI_TXT_GEN_TITLE_PROMPT_RECIPE,
            "post": AI_TXT_GEN_POST_PROMPT_RECIPE,
        },
    }
    AI_TXT_SYS_PROMPT_STYLE_BY_TOPIC = {
        POST_TOPIC_RECIPES: "Your style is humorous, friendly, engaging, and informative. Your tone is warm, approachable, and humorous, making readers feel like they are having a conversation with a knowledgeable friend who cracks family-friendly jokes all the time.",
        POST_TOPIC_OUTFITS: "yOR STYLE IS INFORMATIVE AND TRENDY. YOUR TONE IS FRIENDLY, APPROACHABLE, AND FASHION-FORWARD, MAKING READERS FEEL INSPIRED TO EXPLORE NEW STYLES AND EXPRESS THEMSELVES THROUGH CLOTHING. YOU also have a deep understanding of the domain the outfits are for (e.g., hiking, fishing, etc.) AND INCORPORATE THAT KNOWLEDGE INTO YOUR WRITING.",
    }

    def __init__(self, test: bool = False, callback=print):
        self.test = test
        self.callback = callback

    def __get_verbosity_by_topic__(self, post_topic: str) -> int:
        if self.post_topic == POST_TOPIC_RECIPES:
            return CHATGPT_VERBOSITY_HIGH
        else:
            return CHATGPT_VERBOSITY_MEDIUM

    def write_post(self):
        self.post_title = self.post_title.strip()
        self.post_topic = self.post_topic.strip()

        if self.post_title == "" or self.post_topic == "":
            raise ValueError(f"[ERROR][PostWriter.write_post] post_title and post_topic must be set before calling write_post()")
        if self.test:
            return f"{self.post_title} not modified", f"Test post about {self.post_title} of type {self.post_topic}"

        SYS_PROMPT_BASE = f"yOU ARE A PROFESSIONAL {self.post_topic} WRITER AND COPYWRITER.{self.AI_TXT_SYS_PROMPT_STYLE_BY_TOPIC[self.post_topic]}  You write in a clear and concise manner, making complex topics easy to understand. You have a knack for storytelling and can weave narratives that captivate readers.You are also skilled at SEO writing, ensuring that your content is optimized for search engines while still being enjoyable to read."

        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format="",
            ai_model=CHATGPT_MODEL,
            verbosity=self.__get_verbosity_by_topic__(self.post_topic)
        )

        prompt_config.system_prompt = SYS_PROMPT_BASE + self.AI_TXT_GEN_PROMPTS_BY_TOPIC[self.post_topic]["post"]
        prompt_config.user_prompt = f"Write a detailed {self.post_topic} blog post about '{self.post_title}'. Make sure to follow the structure and style guidelines provided. The post should be engaging, informative, and easy to read. Ensure the content is original and provides value to the readers."

        post_txt = send_prompt_to_openai(prompt_config, self.test)

        if post_txt["error"] != "":
            raise OpenAIAPIError(f"OpenAI API error: {post_txt['error']} '{post_txt['message']}'")

        prompt_config.system_prompt = SYS_PROMPT_BASE + self.AI_TXT_GEN_PROMPTS_BY_TOPIC[self.post_topic]["title"]
        prompt_config.user_prompt = f"Generate a catchy and SEO-friendly blog post title for the following blog post about '{self.post_title}'. The title should be engaging and encourage readers to click on the article. It should also include relevant keywords that would help improve the post's search engine ranking.\nPost text:\n{post_txt['message']}"

        post_title = send_prompt_to_openai(prompt_config, self.test)

        if post_title["error"] != "":
            raise OpenAIAPIError(f"OpenAI API error: {post_title['error']} '{post_title['message']}'")

        txt = post_txt['message']
        txt = html.unescape(txt) if _is_escaped(txt) else txt

        title = post_title['message']
        return title, txt

    def _is_escaped(text: str) -> bool:
        return text != html.unescape(text)

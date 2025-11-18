import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ConfigKeeper')))

import html
from chatgpt_api import *
from chatgpt_settings import *
from settings import *
from ai_txt_gen_settings import *
from notion_config import *

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

    SYS_PROMPT_BASE = f"yOU ARE A PROFESSIONAL {self.post_topic} WRITER AND COPYWRITER.{self.AI_TXT_SYS_PROMPT_STYLE_BY_TOPIC[self.post_topic]}  You write in a clear and concise manner, making complex topics easy to understand. You have a knack for storytelling and can weave narratives that captivate readers.You are also skilled at SEO writing, ensuring that your content is optimized for search engines while still being enjoyable to read."

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
        self.post_type = self.post_type.strip() # single item or roundup

        if self.post_title == "" or self.post_topic == "" or self.post_type == "":
            raise ValueError(f"[ERROR][PostWriter.write_post] post_title, post_topic, and post_type must be set before calling write_post()")
        if self.test:
            return f"{self.post_title} not modified", f"Test post about {self.post_title} of type {self.post_type} in topic {self.post_topic}"

        prompt_config = AIPromptConfig(
            system_prompt="",
            user_prompt="",
            response_format="",
            ai_model=CHATGPT_MODEL,
            verbosity=self.__get_verbosity_by_topic__(self.post_topic)
        )

        prompt_config = self._get_single_post_body_prompts(prompt_config) if self.post_type == POST_POST_TYPE_SINGLE_ITEM_ID else self._get_roundup_post_body_prompts(prompt_config)

        self.callback(f"\n[PostWriter.write_post] Writing the post body...\n")
        post_txt = send_prompt_to_openai(prompt_config, self.test)

        if post_txt["error"] != "":
            raise OpenAIAPIError(f"OpenAI API error: {post_txt['error']} '{post_txt['message']}'")

        prompt_config = self._get_single_post_title_prompts(prompt_config) if self.post_type == POST_POST_TYPE_SINGLE_ITEM_ID else self._get_roundup_post_title_prompts(prompt_config)

        self.callback(f"\n[PostWriter.write_post] Writing the post title...\n")
        post_title = send_prompt_to_openai(prompt_config, self.test)

        if post_title["error"] != "":
            raise OpenAIAPIError(f"OpenAI API error: {post_title['error']} '{post_title['message']}'")

        txt = post_txt['message']
        txt = html.unescape(txt) if self._is_escaped(txt) else txt

        title = post_title['message']
        return title, txt

    def _is_escaped(self, text: str) -> bool:
        return text != html.unescape(text)

    def _get_post_body_prompt(self) -> str:
        prompt = self.AI_TXT_GEN_PROMPTS_BY_TOPIC.get(self.post_topic, {}).get("post", "")
        if not prompt:
            raise ValueError(f"[ERROR][_get_post_body_prompt] No prompt found for post topic '{self.post_topic}'")
        return prompt

    def _get_post_title_prompt(self) -> str:
        prompt = self.AI_TXT_GEN_PROMPTS_BY_TOPIC.get(self.post_topic, {}).get("title", "")
        if not prompt:
            raise ValueError(f"[ERROR][_get_post_title_prompt] No prompt found for post topic '{self.post_topic}'")
        return prompt

    def _get_single_post_body_prompts(self, prompt_config: AIPromptConfig):
        prompt = self._get_post_body_prompt()
        prompt_config.system_prompt = self.SYS_PROMPT_BASE + prompt
        prompt_config.user_prompt = f"""
        Write a detailed {self.post_topic} blog post about '{self.post_title}'. Make sure to follow the structure and style guidelines provided.
        The post should be engaging, informative, and easy to read. Ensure the content is original and provides value to the readers.
        Take into account {self._get_single_plural_subj()}.
        """

        return prompt_config

    def _get_single_post_title_prompts(self, prompt_config: AIPromptConfig):
        prompt = self._get_post_title_prompt()
        prompt_config.system_prompt = self.SYS_PROMPT_BASE + prompt
        prompt_config.user_prompt = f"""
        Generate a catchy and SEO-friendly blog post title for the following blog post about '{self.post_title}'. 
        The title should be engaging and encourage readers to click on the article. It should also include relevant keywords that would help improve the post's search engine ranking.
        Take into account {self._get_single_plural_subj()}.
        Post text:
        {post_txt['message']}"""
        
        return prompt_config

    def _get_roundup_post_body_prompts(self, prompt_config: AIPromptConfig):
        roundup_items = get_post_images_for_blog_url(self.notion_url, self.callback)
        if not roundup_items or len(roundup_items) == 0:
            raise ValueError(f"[ERROR][_get_roundup_post_body_prompts] No roundup items found for post '{self.notion_url}'")

        roundup_titles_str = ", ".join(
            t for t in (str(item.get(BLOG_POST_IMAGES_TITLE_PROP, "")).strip() for item in roundup_items)
            if t
        )
        roundup_descriptions_str = ", ".join(
            d for d in (str(item.get(BLOG_POST_IMAGES_DESCRIPTION_PROP, "")).strip() for item in roundup_items)
            if d
        )
        
        # TODO: For now, it's only recipe roundups => make it more generic for other post topics
        prompt_config.system_prompt = self.SYS_PROMPT_BASE
        prompt_config.user_prompt = f"""
        For each URL below, write an appropriate heading and a 100-150 word text explaining what the recipe is about. And the recipe URL into the text and not heading. Use a cheerful tone
        """

        return prompt_config

    def _get_roundup_post_title_prompts(self, prompt_config: AIPromptConfig):
        # To be implemented in the future
        return self._get_single_post_title_prompts(prompt_config)

    def _get_single_plural_subj(self) -> str:
        if self.post_topic not in POST_TOPIC_AI_PROMPT_NOUNS:
            raise ValueError(
                f"[ERROR][_get_single_plural_subj] Post topic '{self.post_topic}' "
                "does not have a corresponding mapping in POST_TOPIC_AI_PROMPT_NOUNS."
            )
        return (
            "a single item and not plurals"
            if self._get_is_post_type_singular()
            else POST_TOPIC_AI_PROMPT_NOUNS[self.post_topic]
        )
    def _get_is_post_type_singular(self) -> bool:
        return self.post_type == POST_POST_TYPE_SINGLE_VAL
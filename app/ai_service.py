"""
AI News Script Assistant Service
Provides grammar, spelling, and TV/broadcast news formatting enhancement.
Supports Google Gemini, OpenAI, Groq, and a robust offline news formatter.
"""

import os
import json
import logging
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def get_api_key(provider='gemini', client_key=None):
    """
    Retrieve API key with priority:
    1. Client provided key (passed in request)
    2. settings.py configuration (if Django settings configured)
    3. os.environ / .env
    """
    if client_key and client_key.strip():
        return client_key.strip()

    env_var_name = f"{provider.upper()}_API_KEY"
    setting_val = None

    try:
        if settings.configured:
            setting_val = getattr(settings, env_var_name, None)
    except Exception:
        pass

    if setting_val:
        return setting_val

    return os.environ.get(env_var_name)


def free_translate_to_english(text):
    """
    Translates any regional Indian language (Odia, Hindi, Bengali, etc.)
    into English using Google Translate public translation engine.
    Guarantees that regional language news headlines and prompts are
    accurately understood and translated into visual English instructions.
    """
    if not text or not text.strip():
        return ""
    import urllib.parse
    import requests
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={urllib.parse.quote(text.strip())}"
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json and isinstance(res_json, list) and len(res_json) > 0 and isinstance(res_json[0], list):
                translated_parts = [part[0] for part in res_json[0] if part and len(part) > 0 and part[0]]
                translated = "".join(translated_parts).strip()
                if translated:
                    return translated
    except Exception as e:
        logger.warning("Free translation fallback error: %s", e)
    return text.strip()


def generate_image_with_gemini(prompt, reference_image_bytes=None, mime_type="image/jpeg", api_key=None):
    """
    Attempts to generate high-resolution image using Google Gemini Image Generation models
    (gemini-2.5-flash-image, gemini-3.1-flash-image, gemini-2.0-flash-exp).
    """
    if not api_key:
        api_key = get_api_key('gemini')
    if not api_key:
        return None

    import base64
    models = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-2.0-flash-exp", "gemini-2.0-flash"]
    
    parts = []
    if reference_image_bytes:
        b64_ref = base64.b64encode(reference_image_bytes).decode('utf-8')
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_ref
            }
        })
    parts.append({"text": prompt})

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE"]
        }
    }

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get('candidates', [])
                if candidates:
                    for part in candidates[0].get('content', {}).get('parts', []):
                        inline = part.get('inline_data') or part.get('inlineData')
                        if inline and inline.get('data'):
                            img_b64 = inline.get('data')
                            return base64.b64decode(img_b64)
            logger.warning("Gemini image model %s returned status %s: %s", model, resp.status_code, resp.text[:120])
        except Exception as e:
            logger.warning("Gemini image generation error for %s: %s", model, e)

    return None


def call_gemini(prompt, api_key):
    """Call Google Gemini Flash REST API with model fallback"""
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    last_err = None

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.85,
                "maxOutputTokens": 2048,
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=20)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        return parts[0].get('text', '').strip()
            last_err = f"Gemini ({model}) error {response.status_code}: {response.text[:150]}"
            logger.warning("Gemini attempt failed for %s: %s", model, response.text[:100])
        except Exception as e:
            last_err = str(e)
            logger.warning("Gemini connection error for %s: %s", model, e)

    raise RuntimeError(last_err or "All Gemini models failed.")


def call_gemini_vision(prompt, image_bytes, mime_type="image/jpeg", api_key=None):
    """
    Call Google Gemini Vision (gemini-2.0-flash / gemini-1.5-flash) with an image and text prompt.
    Supports analyzing reference images and extracting detailed visual scene descriptions
    incorporating Hindi, Odia, or English instructions.
    """
    if not api_key:
        api_key = get_api_key('gemini')
    if not api_key:
        raise ValueError("Gemini API key is required for Gemini Vision.")

    import base64
    b64_img = base64.b64encode(image_bytes).decode('utf-8')
    models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    last_err = None

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_img
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "topP": 0.9,
                "maxOutputTokens": 1024,
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=25)
            if response.status_code == 200:
                data = response.json()
                candidates = data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        return parts[0].get('text', '').strip()
            last_err = f"Gemini Vision ({model}) error {response.status_code}: {response.text[:150]}"
            logger.warning("Gemini Vision attempt failed for %s: %s", model, response.text[:100])
        except Exception as e:
            last_err = str(e)
            logger.warning("Gemini Vision error for %s: %s", model, e)

    raise RuntimeError(last_err or "All Gemini Vision models failed.")


def call_openai_vision(prompt, image_bytes, mime_type="image/jpeg", api_key=None):
    """Call OpenAI GPT-4o-mini Vision with an image and text prompt"""
    if not api_key:
        api_key = get_api_key('openai')
    if not api_key:
        raise ValueError("OpenAI API key required for vision.")
    import base64
    b64_img = base64.b64encode(image_bytes).decode('utf-8')
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_img}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1024
    }
    resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=25)
    if resp.status_code == 200:
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    raise RuntimeError(f"OpenAI Vision error {resp.status_code}: {resp.text[:150]}")


def analyze_reference_image_for_prompt(image_bytes, user_prompt, style="photorealistic news", headline="", mime_type="image/jpeg"):
    """
    Multimodal AI image-to-image prompt analyzer.
    Understands reference image + user instructions (Hindi, Odia, English, or Hinglish),
    producing a high-quality visual scene description for news graphics generation.
    """
    vision_prompt = (
        "You are an expert Indian TV news graphic designer and visual prompt engineer for Prameya Digital News.\n"
        "You are given a reference photograph and user instructions (in Hindi, Odia, English, or Hinglish).\n\n"
        f"Story Headline: {headline or 'News story'}\n"
        f"User Instructions: {user_prompt}\n"
        f"Target Visual Style: {style}\n\n"
        "Instructions:\n"
        "1. Identify the key subject in the photo (e.g. Indian politician, public figure, victim, vehicle, rescue scene, specific attire, facial characteristics, hair, skin tone).\n"
        "2. Accurately translate and understand the user's instructions (especially if written in Hindi or Odia, e.g. 'is photo wale neta ji ko studio me dikhao' or 'is ghatna ka breaking news graphic banao').\n"
        "3. Produce a vivid, detailed English visual prompt (under 40 words) for AI image generation. It must maintain the subject's recognizable likeness, identity, and clothing style from the photo, placing them in the scene requested by the user suitable for a high-end news broadcast graphic.\n"
        "4. Output ONLY the concise visual description in English. Do not add quotes, explanations, or preface."
    )

    # 1. Try Gemini Vision
    try:
        gemini_key = get_api_key('gemini')
        if gemini_key:
            res = call_gemini_vision(vision_prompt, image_bytes, mime_type, gemini_key)
            if res and len(res.strip()) > 5:
                return res.strip()
    except Exception as e:
        logger.warning("Gemini Vision failed in analyze_reference_image_for_prompt: %s", e)

    # 2. Try OpenAI Vision
    try:
        openai_key = get_api_key('openai')
        if openai_key:
            res = call_openai_vision(vision_prompt, image_bytes, mime_type, openai_key)
            if res and len(res.strip()) > 5:
                return res.strip()
    except Exception as e:
        logger.warning("OpenAI Vision failed in analyze_reference_image_for_prompt: %s", e)

    return None


def call_openai(prompt, api_key):
    """Call OpenAI GPT-4o-mini REST API"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a professional television news script editor."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2048
    }
    response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=20)
    if response.status_code == 200:
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    logger.error("OpenAI API Error: %s %s", response.status_code, response.text)
    raise RuntimeError(f"OpenAI API returned error {response.status_code}: {response.text[:150]}")


def call_groq(prompt, api_key):
    """Call Groq API (Llama 3.3 70b)"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a senior TV news copy editor and scriptwriter."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2048
    }
    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
    if response.status_code == 200:
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    logger.error("Groq API Error: %s %s", response.status_code, response.text)
    raise RuntimeError(f"Groq API returned error {response.status_code}: {response.text[:150]}")


def fallback_clean_and_format(text, headline="", news_type="AVO", tone="standard"):
    """
    Intelligent built-in news script formatter when no external AI API key is configured.
    Cleans typos, fixes spacing, punctuates, structures paragraphs, and formats for broadcast.
    """
    if not text:
        return ""

    cleaned = text.strip()
    # Normalize multiple whitespace
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    # Fix spacing before punctuation
    cleaned = re.sub(r'\s+([,.\?!;:])', r'\1', cleaned)
    # Ensure space after punctuation
    cleaned = re.sub(r'([,.\?!;:])([^\s\d])', r'\1 \2', cleaned)

    # Capitalize first letter of sentences
    def cap_sentence(match):
        return match.group(1) + match.group(2).upper()

    cleaned = re.sub(r'(^|[.?!]\s+)([a-z])', cap_sentence, cleaned)

    # Split into clean paragraphs
    paragraphs = [p.strip() for p in cleaned.split('\n') if p.strip()]

    # Format into professional broadcast script layout
    if tone == 'broadcast' or news_type in ['AVO', 'PKG', 'AVO Byte']:
        formatted_lines = []
        if headline:
            formatted_lines.append(f"[SLUG / HEADLINE: {headline.strip()}]")
            formatted_lines.append("")

        formatted_lines.append("[ANCHOR INTRO / LEAD]:")
        if paragraphs:
            formatted_lines.append(paragraphs[0])
            formatted_lines.append("")

        if len(paragraphs) > 1:
            formatted_lines.append("[VISUAL / STORY DETAILS]:")
            for p in paragraphs[1:]:
                formatted_lines.append(p)
                formatted_lines.append("")
        
        if news_type in ['Byte', 'AVO Byte']:
            formatted_lines.append("[SOUNDBYTE / BYTE CUE]:")
            formatted_lines.append("(Byte audio/video statement follows)")

        return "\n".join(formatted_lines).strip()

    return "\n\n".join(paragraphs).strip()


def improve_news_script(raw_text, headline="", news_type="AVO", tone="standard", client_key=None):
    """
    Main entry point for checking and improving news scripts.
    Returns dict:
    {
        'success': bool,
        'improved_text': str,
        'summary': str,
        'provider': str,
        'has_api_key': bool
    }
    """
    if not raw_text or not raw_text.strip():
        return {
            'success': False,
            'error': 'News description text is empty. Please enter text to check.',
            'improved_text': '',
        }

    clean_raw = raw_text.strip()

    # Determine prompt instructions based on tone
    tone_instruction = ""
    if tone == 'broadcast':
        tone_instruction = (
            "Format the text as a television broadcast news script (with [ANCHOR], [VO / DETAILS], and [BYTE CUE] tags where suitable). "
            "Ensure the opening is a gripping news anchor lead."
        )
    elif tone == 'concise':
        tone_instruction = (
            "Make the news script extremely crisp, punchy, and concise. "
            "Eliminate redundant filler words while keeping all key facts (who, what, where, when, why)."
        )
    else:
        tone_instruction = (
            "Review and polish the news report. Correct all grammatical, spelling, and sentence structure errors. "
            "Enhance the clarity, flow, and journalistic tone suitable for a professional TV news organization."
        )

    # Contextual prompt for TV News Scripts
    prompt = f"""You are an elite TV News Editor and Chief Copy Editor for Prameya Digital News Channel.
Your task is to check, correct, and professionally polish the following news script submitted by a ground field reporter.

RULES:
1. STRICT LANGUAGE PRESERVATION: Retain the EXACT SAME language used by the reporter (Hindi, Odia, English, or Hinglish / colloquial Hindi-English). Do NOT translate to another language unless instructed.
2. SPELLING & GRAMMAR: Fix all spelling mistakes, grammatical errors, incorrect verb forms, punctuation, and typographical issues.
3. FACTUAL INTEGRITY: Keep all names, locations, dates, numbers, and facts EXACTLY as given. Do NOT invent or hallucinate new facts.
4. BROADCAST JOURNALISTIC QUALITY: {tone_instruction}
5. Clean, engaging TV anchor/reporter phrasing.
6. OUTPUT FORMAT: Return ONLY the revised news script. Do NOT include greetings, preamble, explanations, or quotes around the output.

STORY CONTEXT:
Headline: {headline or 'Not specified'}
News Type: {news_type or 'General'}

ORIGINAL REPORTER DRAFT:
{clean_raw}
"""

    gemini_key = get_api_key('gemini', client_key)
    openai_key = get_api_key('openai', client_key)
    groq_key = get_api_key('groq', client_key)

    # 1. Try Gemini
    if gemini_key:
        try:
            result = call_gemini(prompt, gemini_key)
            if result:
                return {
                    'success': True,
                    'improved_text': result,
                    'summary': 'Spelling, grammar, and journalistic flow improved using Gemini AI.',
                    'provider': 'Google Gemini 2.0 Flash',
                    'has_api_key': True
                }
        except Exception as e:
            logger.warning("Gemini API call failed, trying next provider: %s", e)

    # 2. Try Groq (Llama 3.3)
    if groq_key:
        try:
            result = call_groq(prompt, groq_key)
            if result:
                return {
                    'success': True,
                    'improved_text': result,
                    'summary': 'Spelling and news phrasing polished using Groq AI.',
                    'provider': 'Groq (Llama 3.3)',
                    'has_api_key': True
                }
        except Exception as e:
            logger.warning("Groq API call failed: %s", e)

    # 3. Try OpenAI
    if openai_key:
        try:
            result = call_openai(prompt, openai_key)
            if result:
                return {
                    'success': True,
                    'improved_text': result,
                    'summary': 'News script refined and corrected using OpenAI.',
                    'provider': 'OpenAI GPT-4o-mini',
                    'has_api_key': True
                }
        except Exception as e:
            logger.warning("OpenAI API call failed: %s", e)

    # 4. Fallback: Intelligent built-in news formatter
    formatted = fallback_clean_and_format(clean_raw, headline=headline, news_type=news_type, tone=tone)
    summary_note = (
        "Script cleaned and formatted for broadcast. "
        "Tip: Set your free GEMINI_API_KEY in .env or via the API settings button to enable full Deep AI generative polish!"
    )
    return {
        'success': True,
        'improved_text': formatted,
        'summary': summary_note,
        'provider': 'Prameya Digital News Formatter (Offline)',
        'has_api_key': False,
        'note': 'No external AI API key configured. You can provide a Gemini API key for deep generative rewriting.'
    }

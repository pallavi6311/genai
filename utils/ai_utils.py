"""Gemini-powered helpers for image understanding, speech scripting, and adaptive communication training."""

import os
import json
import re
from io import BytesIO
from typing import Optional

import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

_LANG_NAMES = {"en": "English", "hi": "Hindi", "ta": "Tamil", "ja": "Japanese"}

_model_cache = {}


def _get_api_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")


def _get_model(model_name: str = "gemini-flash-latest"):
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        if model_name not in _model_cache:
            _model_cache[model_name] = genai.GenerativeModel(model_name)
        return _model_cache[model_name]
    except Exception:
        return None


def gemini_available() -> bool:
    return (
        _get_model() is not None
        or _get_model("gemini-1.5-pro") is not None
        or _get_model("gemini-1.5-flash") is not None
    )


def generate_image_description(
    image_bytes: bytes,
    filename: str = "image",
    mime_type: str = "image/jpeg",
    output_language: str = "English",
) -> str:
    models = [
        _get_model("gemini-flash-latest"),
        _get_model("gemini-3.1-flash-lite"),
        _get_model("gemini-3.5-flash-lite"),
    ]
    models = [model for model in models if model is not None]
    if not models:
        return "Gemini is unavailable, so an accurate visual description could not be generated."

    prompt = (
        "Inspect this image carefully and produce an accurate description of only what is visibly present. "
        "Start with the overall scene, then identify every important visible person, animal, object, "
        "color, position, action, and interaction. Mention readable text exactly when it is clear. "
        "Describe the setting, lighting, and apparent emotion only when visual evidence supports it. "
        "Use precise nouns instead of vague phrases such as 'meaningful scene' or 'some objects'. "
        "Do not guess names, identities, ages, locations, brands, or intentions. If a detail is unclear, "
        "say that it is unclear. Do not mention image dimensions, file names, datasets, or this prompt. "
        f"Return one well-organized paragraph suitable for reading aloud in {output_language}. "
        f"Do not write in English unless the selected output language is English."
    )

    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        normalized_image = BytesIO()
        image.save(normalized_image, format="JPEG", quality=92)
        image_bytes = normalized_image.getvalue()
    except Exception:
        return "The uploaded file is not a readable image. Please upload a valid JPG or PNG image."

    errors = []
    for model in models:
        try:
            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": image_bytes},
                prompt,
            ])
            text = getattr(response, "text", "")
            if text and text.strip():
                return text.strip()
            errors.append("Gemini returned no text")
        except Exception as exc:
            errors.append(type(exc).__name__)

    error_summary = ", ".join(dict.fromkeys(errors))
    return (
        "Gemini could not analyze this image. Check that GEMINI_API_KEY is valid and that the model has access "
        f"to image input. Technical details: {error_summary or 'empty response'}."
    )


def translate_text(text: str, target_lang_code: str) -> str:
    target_name = _LANG_NAMES.get(target_lang_code, "English")
    if target_lang_code == "en":
        return text

    model = _get_model() or _get_model("gemini-1.5-flash")
    if model is None:
        return text

    prompt = f"Translate the following text into {target_name}. Return only the translated text and nothing else.\n\n{text}"
    try:
        response = model.generate_content(prompt)
        result = getattr(response, "text", "")
        return result.strip() if result and result.strip() else text
    except Exception:
        return text


def translate_image_description(description: str, target_lang_code: str) -> str:
    """Translate a grounded image description without adding or removing visual facts."""
    if not description or target_lang_code == "en":
        return description

    target_name = _LANG_NAMES.get(target_lang_code, "English")
    model = _get_model() or _get_model("gemini-flash-latest") or _get_model("gemini-3.1-flash-lite")
    if model is None:
        return description

    prompt = (
        f"Translate this image description into natural {target_name}. Preserve every visible fact, "
        "object, action, color, position, and readable text exactly. Do not summarize, add details, "
        "guess, or mention translation. Return only the translated description.\n\n"
        f"Description:\n{description}"
    )
    try:
        response = model.generate_content(prompt)
        result = getattr(response, "text", "")
        if result and result.strip():
            return result.strip()
    except Exception:
        pass
    return description


def answer_question_from_context(
    caption: str,
    ocr_text: str,
    question: str,
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/jpeg",
) -> str:
    if not question.strip():
        raise ValueError("Enter a question about the image.")
    if not image_bytes:
        raise ValueError("Analyze an image before asking a question about it.")

    model = (
        _get_model("gemini-flash-latest")
        or _get_model("gemini-3.1-flash-lite")
        or _get_model("gemini-3.5-flash-lite")
    )
    if model is None:
        raise RuntimeError("Gemini is unavailable. Check your API key and try again.")

    prompt = (
        "Answer the user's specific question about the attached image directly and concisely. "
        "Inspect the image itself; use the description and OCR only as additional context. "
        "If asked to identify a logo, name the recognizable brand or organization and distinguish "
        "that from legal trademark ownership. Use general knowledge to identify a recognizable logo, "
        "but do not claim a person or organization owns it unless the evidence supports that claim. "
        "If the image does not provide enough evidence, say what can and cannot be determined instead "
        "of repeating the image description. Do not invent details.\n\n"
        f"Image description: {caption}\n"
        f"OCR text: {ocr_text or 'No readable text detected.'}\n\n"
        f"User's question: {question}"
    )
    response = model.generate_content([
        {"mime_type": mime_type or "image/jpeg", "data": image_bytes},
        prompt,
    ])
    result = getattr(response, "text", "")
    if not result or not result.strip():
        raise RuntimeError("Gemini returned no answer. Please try asking the question again.")
    return result.strip()


def generate_image_questions(caption: str, ocr_text: str, language: str, level: str = "Beginner") -> list[dict]:
    language_name = _LANG_NAMES.get(language, language)
    fallback = [
        {
            "question": {
                "English": "What can you see in this image?",
                "Hindi": "आप इस तस्वीर में क्या देख सकते हैं?",
                "Tamil": "இந்தப் படத்தில் நீங்கள் என்ன பார்க்கிறீர்கள்?",
                "Japanese": "この画像には何が見えますか。",
            }.get(language_name, "What can you see in this image?"),
            "translation": "What can you see in this image?",
        },
        {
            "question": {
                "English": "What is happening in the image?",
                "Hindi": "इस तस्वीर में क्या हो रहा है?",
                "Tamil": "இந்தப் படத்தில் என்ன நடக்கிறது?",
                "Japanese": "この画像では何が起きていますか。",
            }.get(language_name, "What is happening in the image?"),
            "translation": "What is happening in the image?",
        },
    ]
    models = [
        _get_model("gemini-flash-latest"),
        _get_model("gemini-3.1-flash-lite"),
        _get_model("gemini-3.5-flash-lite"),
    ]
    models = [model for model in models if model is not None]
    if not models:
        return fallback

    prompt = (
        f"You are a {language_name} communication teacher. Create 3 spoken questions about this image. "
        f"Learner level: {level}. Ask about visible objects, people, actions, setting, and context. "
        "Every question must be answerable from the provided description or OCR; do not ask for hidden facts "
        "or guess identities. Return JSON only as an array of objects with question and translation keys. "
        f"Write question in {language_name} and translation in English.\n\n"
        f"Image description: {caption}\nDetected text: {ocr_text or 'None'}"
    )
    try:
        response = model.generate_content(prompt)
        text = (getattr(response, "text", "") or "").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
        value = json.loads(text)
        if isinstance(value, list):
            questions = [item for item in value if item.get("question") and item.get("translation")]
            if questions:
                return questions[:5]
    except Exception:
        pass
    return fallback


def generate_story(
    scenario: str,
    mode: str = "Original Story",
    output_language: str = "English",
) -> Optional[str]:
    model = _get_model() or _get_model("gemini-flash-latest") or _get_model("gemini-3.1-flash-lite")
    if model is None:
        return None

    style_hint = {
        "Short": "a concise and natural 2-sentence description",
        "Detailed": "a rich descriptive paragraph of about 80 words",
        "Accessibility": "a calm, clear, screen-reader-friendly description",
        "Original Story": "a warm and natural short narrative with emotional flow",
    }.get(mode, "a warm short description")

    prompt = (
        f"Write {style_hint} in {output_language} as a clearly fictional story inspired by the visual facts below. "
        "This must be different from an image description. Do not list objects, do not summarize the picture, "
        "and never say 'this image shows' or 'the image depicts'. Give the visible characters fictional names, "
        "a personal goal or feeling, one small event or problem, at least one line of natural dialogue when suitable, "
        "and a meaningful ending. Keep the characters and setting consistent with the visual facts, but add imaginative "
        "story details. Return only the story, without headings or analysis. "
        f"Visual facts to inspire the story:\n{scenario}"
    )
    try:
        response = model.generate_content(prompt)
        result = getattr(response, "text", "")
        if result and result.strip():
            story = result.strip()
            description_markers = (
                "this image shows",
                "the image shows",
                "the image depicts",
                "in this picture",
                "this scene shows",
            )
            if not story.lower().startswith(description_markers) and story.lower() != scenario.strip().lower():
                return story
    except Exception:
        pass
    return None


def generate_practice_plan(
    level: str,
    language: str,
    score: float,
    focus_areas: Optional[list[str]] = None,
) -> str:
    focus_summary = ", ".join(area.strip() for area in (focus_areas or []) if area.strip())
    fallback_plan = (
        f"Current level: {level} ({score:.0f}/100) in {language}.\n"
        f"Main focus: {focus_summary or 'clear pronunciation, correct grammar, and complete answers'}.\n"
        "7-day speaking schedule (15 minutes each day):\n"
        "Day 1: Listen to and repeat the corrected answer slowly; focus on clear sounds.\n"
        "Day 2: Practise the grammar corrections and make five new sentences.\n"
        "Day 3: Answer three everyday questions in complete sentences and record yourself.\n"
        "Day 4: Repeat the pronunciation practice, paying attention to rhythm and pauses.\n"
        "Day 5: Use the recommended vocabulary in a one-minute answer.\n"
        "Day 6: Re-answer today's question without reading; compare it with your first attempt.\n"
        "Day 7: Record a new answer and review your grammar, pronunciation, and confidence.\n"
        "Track your next score and focus first on the skill that needs the most practice."
    )
    model = _get_model() or _get_model("gemini-1.5-flash")
    if model is None:
        return fallback_plan

    prompt = (
        f"Create a focused communication improvement plan for a learner with level '{level}' "
        f"in {language}. Their recent speaking score was {score:.0f}/100. "
        f"Specific feedback and weak areas: {focus_summary or 'not provided'}. "
        "Give a practical 7-day speaking schedule, one clearly labelled task per day, "
        "with a 10- to 20-minute activity and a measurable speaking goal. "
        "Prioritize the learner's weak areas, include pronunciation and grammar practice, "
        "and finish with a recorded self-check. Keep it supportive and appropriate to their level."
    )
    try:
        response = model.generate_content(prompt)
        result = getattr(response, "text", "")
        if result and result.strip():
            return result.strip()
    except Exception:
        pass

    return fallback_plan


def _parse_json_response(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


def generate_scene_challenge_questions(
    caption: str,
    ocr_text: str,
    language: str,
    level: str = "Beginner",
) -> list[dict]:
    language_name = _LANG_NAMES.get(language, language)
    fallback_questions = {
        "English": [
            ("Observe", "What details can you see in this scene?", "What details can you see in this scene?", "Name visible people, objects, actions, or colors."),
            ("Explain", "What do you think is happening, and which visible clues support your idea?", "What do you think is happening, and which visible clues support your idea?", "Explain your idea using evidence from the scene."),
            ("Imagine", "If this scene continued, what might happen next? Give one reason.", "If this scene continued, what might happen next? Give one reason.", "Create a possibility and support it with a reason."),
        ],
        "Hindi": [
            ("Observe", "इस दृश्य में आपको कौन-कौन सी बातें दिखाई दे रही हैं?", "What details can you see in this scene?", "दिखाई देने वाले लोगों, वस्तुओं, गतिविधियों या रंगों का नाम बताएं।"),
            ("Explain", "आपके विचार से यहाँ क्या हो रहा है, और कौन-से दृश्य संकेत आपके विचार का समर्थन करते हैं?", "What do you think is happening, and which visible clues support your idea?", "दृश्य के संकेतों के आधार पर अपना विचार समझाएँ।"),
            ("Imagine", "अगर यह दृश्य आगे बढ़े, तो आगे क्या हो सकता है? एक कारण भी बताइए।", "If this scene continued, what might happen next? Give one reason.", "एक संभावना सोचें और उसका कारण बताएं।"),
        ],
        "Tamil": [
            ("Observe", "இந்தக் காட்சியில் நீங்கள் என்னென்ன விவரங்களைப் பார்க்கிறீர்கள்?", "What details can you see in this scene?", "காணப்படும் மனிதர்கள், பொருட்கள், செயல்கள் அல்லது நிறங்களைக் குறிப்பிடுங்கள்."),
            ("Explain", "இங்கே என்ன நடக்கிறது என்று நினைக்கிறீர்கள்? உங்கள் கருத்துக்கு ஆதரவாக எந்தக் காட்சி விவரங்கள் உள்ளன?", "What do you think is happening, and which visible clues support your idea?", "காட்சியில் உள்ள ஆதாரங்களைக் கொண்டு உங்கள் கருத்தை விளக்குங்கள்."),
            ("Imagine", "இந்தக் காட்சி தொடர்ந்தால் அடுத்து என்ன நடக்கலாம்? ஒரு காரணத்தையும் சொல்லுங்கள்.", "If this scene continued, what might happen next? Give one reason.", "ஒரு சாத்தியத்தை கற்பனை செய்து அதற்கான காரணத்தைக் கூறுங்கள்."),
        ],
        "Japanese": [
            ("Observe", "この場面にはどのようなものが見えますか。", "What details can you see in this scene?", "見える人、物、行動、色を挙げてください。"),
            ("Explain", "ここで何が起きていると思いますか。そう考えた手がかりも説明してください。", "What do you think is happening, and which visible clues support your idea?", "場面に見える手がかりを使って考えを説明してください。"),
            ("Imagine", "この場面が続くとしたら、次に何が起きると思いますか。理由も一つ挙げてください。", "If this scene continued, what might happen next? Give one reason.", "可能性を考え、その理由を説明してください。"),
        ],
    }
    fallback = [
        {"stage": stage, "question": question, "translation": translation, "goal": goal}
        for stage, question, translation, goal in fallback_questions.get(
            language_name, fallback_questions["English"]
        )
    ]

    models = [
        _get_model("gemini-flash-latest"),
        _get_model("gemini-3.1-flash-lite"),
        _get_model("gemini-3.5-flash-lite"),
    ]
    models = [model for model in models if model is not None]
    if not models:
        return fallback

    prompt = (
        f"Create exactly three spoken language-learning questions in {language_name} for a {level} learner. "
        "Return a JSON array with exactly these stages in this order: Observe, Explain, Imagine. "
        "Each item must contain stage, question, translation, and goal. "
        "Observe asks for directly visible details only. Explain asks the learner to interpret the scene "
        "and support the interpretation with visible clues; do not present uncertain details as facts. "
        "Imagine invites a clearly hypothetical continuation, and must not be graded as an image fact. "
        "Write question and goal in the selected language, and translation in English. "
        "Return only valid JSON.\n\n"
        f"Image description: {caption}\n"
        f"Readable text in image: {ocr_text or 'None detected.'}"
    )
    for model in models:
        try:
            response = model.generate_content(prompt)
            text = (getattr(response, "text", "") or "").strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
            value = json.loads(text)
            if not isinstance(value, list):
                continue
            questions_by_stage = {
                item.get("stage"): item
                for item in value
                if isinstance(item, dict)
                and item.get("stage") in {"Observe", "Explain", "Imagine"}
                and item.get("question")
                and item.get("translation")
                and item.get("goal")
            }
            if all(stage in questions_by_stage for stage in ("Observe", "Explain", "Imagine")):
                return [questions_by_stage[stage] for stage in ("Observe", "Explain", "Imagine")]
        except Exception:
            continue
    return fallback


def generate_language_question(language: str, level: str, focus: str) -> dict:
    language_name = _LANG_NAMES.get(language, language)
    fallback = {
        "question": {
            "English": "What did you do today?",
            "Hindi": "आपने आज क्या किया?",
            "Tamil": "இன்று நீங்கள் என்ன செய்தீர்கள்?",
            "Japanese": "今日は何をしましたか。",
        }.get(language_name, "What did you do today?"),
        "translation": "What did you do today?",
        "target_words": [],
    }
    model = _get_model() or _get_model("gemini-1.5-pro") or _get_model("gemini-1.5-flash")
    if model is None:
        return fallback

    prompt = (
        f"You are a patient {language_name} conversation teacher. Create one practical question for a learner. "
        f"Learner level: {level}. Conversation focus: {focus}. "
        f"Use natural {language_name} appropriate for the level, not textbook-gibberish. "
        "Return JSON only with exactly these keys: question, translation, target_words. "
        f"question must be in {language_name}; translation must be in English; target_words must be an array of 1 to 3 useful words in {language_name}."
    )
    try:
        response = model.generate_content(prompt)
        result = _parse_json_response(getattr(response, "text", ""))
        if result.get("question") and result.get("translation"):
            return {
                "question": str(result["question"]),
                "translation": str(result["translation"]),
                "target_words": result.get("target_words", []),
            }
    except Exception:
        pass
    return fallback


def evaluate_language_answer(language: str, question: str, answer: str, level: str) -> dict:
    language_name = _LANG_NAMES.get(language, language)
    fallback = {
        "score": 0,
        "level": "Beginner",
        "is_correct": False,
        "feedback": f"Gemini could not evaluate this answer. Please try again with a complete {language_name} sentence.",
        "corrected_answer": answer,
        "corrections": [],
        "vocabulary": [],
        "pronunciation": "Pronunciation guidance is unavailable until Gemini evaluates the answer.",
        "usage": "Try using the corrected sentence in a short conversation.",
    }
    model = _get_model() or _get_model("gemini-1.5-pro") or _get_model("gemini-1.5-flash")
    if model is None:
        return fallback

    prompt = (
        f"You are a careful {language_name} language teacher evaluating a learner's answer. "
        f"Learner level: {level}.\nQuestion in {language_name}: {question}\nLearner answer: {answer}\n\n"
        "Evaluate meaning, grammar, politeness, naturalness, and whether it answers the question. "
        "Do not penalize a correct answer for using a different natural expression. "
        "Return JSON only with exactly these keys: score (integer 0-100), level, is_correct, feedback, "
        "corrected_answer, corrections, vocabulary, pronunciation, usage. "
        "corrections must be an array of objects with original, correction, and explanation. "
        "vocabulary must be an array of objects with word, meaning, reading, pronunciation, and usage_example. "
        "pronunciation must explain how to say the corrected answer. Use romanization when useful and include stress or pronunciation guidance appropriate for the language. "
        "usage must explain when the recommended words or sentence are appropriate. "
        "Keep all explanations clear and supportive."
    )
    try:
        response = model.generate_content(prompt)
        result = _parse_json_response(getattr(response, "text", ""))
        if result.get("feedback") and result.get("corrected_answer"):
            result.setdefault("score", 0)
            result.setdefault("level", "Beginner")
            result.setdefault("is_correct", int(result["score"]) >= 70)
            result.setdefault("corrections", [])
            result.setdefault("vocabulary", [])
            result.setdefault("pronunciation", "Read the corrected sentence slowly and clearly.")
            result.setdefault("usage", "Use the corrected sentence in a similar everyday situation.")
            return result
    except Exception:
        pass
    return fallback


def evaluate_audio_answer(
    language: str,
    question: str,
    audio_bytes: bytes,
    mime_type: str,
    level: str,
) -> dict:
    language_name = _LANG_NAMES.get(language, language)
    fallback = evaluate_language_answer(language, question, "", level)
    if not audio_bytes:
        fallback["feedback"] = "No audio was captured. Please record an answer or upload an audio file before evaluating."
        fallback["error"] = "empty_audio"
        return fallback
    fallback["feedback"] = (
        f"Gemini could not understand the {language_name} audio. Please record again in a quiet place "
        "and speak one complete sentence."
    )
    models = [
        _get_model("gemini-flash-latest"),
        _get_model("gemini-3.1-flash-lite"),
        _get_model("gemini-3.5-flash-lite"),
    ]
    models = [model for model in models if model is not None]
    if not models:
        fallback["error"] = "model_unavailable"
        return fallback

    prompt = (
        f"You are a careful {language_name} conversation teacher. Evaluate this learner's recorded audio. "
        f"The question was: {question}\nLearner level: {level}\n\n"
        f"First transcribe only the clearly spoken answer in {language_name}. Then evaluate whether it answers "
        "the question, including meaning, grammar, politeness, naturalness, and pronunciation. "
        "Return JSON only with exactly these keys: transcript, score, grammar_score, pronunciation_score, "
        "fluency_score, content_score, level, is_correct, feedback, corrected_answer, corrections, "
        "vocabulary, pronunciation, usage. "
        "All five scores must be integers from 0 to 100. score is the overall speaking score; "
        "grammar_score rates grammar accuracy, pronunciation_score rates how clearly the words were spoken, "
        "fluency_score rates flow and pacing, and content_score rates how well the answer addresses the question. "
        "corrections must be an array of objects with original, correction, and explanation. "
        "vocabulary must be an array of objects with word, meaning, reading, pronunciation, and usage_example. "
        "pronunciation must identify useful pronunciation improvements for the recorded answer. "
        "Do not invent words that cannot be heard. If the audio is unclear, say so and give a low score."
    )
    errors = []
    for model in models:
        try:
            response = model.generate_content([
                {"mime_type": mime_type or "audio/wav", "data": audio_bytes},
                prompt,
            ])
            result = _parse_json_response(getattr(response, "text", ""))
            if result.get("transcript") and result.get("feedback"):
                result.setdefault("score", 0)
                result.setdefault("level", "Beginner")
                result.setdefault("is_correct", int(result["score"]) >= 70)
                result.setdefault("corrected_answer", result["transcript"])
                result.setdefault("corrections", [])
                result.setdefault("vocabulary", [])
                result.setdefault("pronunciation", "Repeat the corrected answer slowly and clearly.")
                result.setdefault("usage", "Use the corrected sentence in a similar everyday situation.")
                return result
            errors.append("empty_response")
        except Exception as exc:
            errors.append(type(exc).__name__)
    fallback["error"] = ", ".join(dict.fromkeys(errors)) or "empty_response"
    if "ResourceExhausted" in errors:
        fallback["feedback"] = (
            "Gemini's audio quota or rate limit has been reached. Wait a few minutes, check your Gemini API quota, "
            "or use another API key/project, then submit the recording again."
        )
    else:
        fallback["feedback"] = (
            f"Gemini could not understand the {language_name} audio. Please record again in a quiet place "
            f"and speak one complete sentence. Technical details: {fallback['error']}."
        )
    return fallback


def generate_japanese_question(level: str, focus: str) -> dict:
    return generate_language_question("ja", level, focus)


def evaluate_japanese_answer(question: str, answer: str, level: str) -> dict:
    return evaluate_language_answer("ja", question, answer, level)

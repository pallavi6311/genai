import os
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import streamlit as st
from dotenv import find_dotenv, load_dotenv
from PIL import Image

from utils import ai_utils
from utils import ocr as ocr_utils
from utils import tts as tts_utils
from utils.custom import css_code

load_dotenv(find_dotenv())

PROJECT_DIRECTORY = Path(__file__).parent
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _gemini_ready() -> bool:
    if not hasattr(ai_utils, "gemini_available"):
        return False
    try:
        return bool(ai_utils.gemini_available())
    except Exception:
        return False


def fallback_image_caption(filename: str) -> str:
    cleaned = Path(filename).stem.replace("_", " ").replace("-", " ")
    cleaned = " ".join(cleaned.split())
    if cleaned:
        return f"A meaningful scene showing {cleaned}, with people, objects, emotion, and a clear everyday context."
    return "A meaningful visual scene with people, objects, and emotional context in a natural setting."


def build_default_narration(caption: str, mode: str) -> str:
    scenario = caption.strip() or "a quiet place"
    if mode == "Short":
        return f"In a fictional moment, two friends pause at {scenario} and discover a small reason to smile together."
    if mode == "Detailed":
        return (
            f"In a fictional story inspired by {scenario}, the characters share a quiet moment before an unexpected detail changes their plans. "
            "They help one another, discover something hopeful, and leave the scene with a stronger feeling of friendship."
        )
    if mode == "Accessibility":
        return f"This fictional story begins at {scenario}. The characters notice one another, respond to a small event, and share a calm, supportive moment."
    return f"At {scenario}, a small adventure begins when the characters notice something unusual nearby. Their curiosity brings them together, and by the end of the story they understand that an ordinary moment can become a treasured memory."


def build_fallback_story(caption: str, language: str) -> str:
    if language == "Hindi":
        return f"एक काल्पनिक कहानी में, इस दृश्य के पात्रों ने एक शांत क्षण में एक छोटी समस्या देखी। उन्होंने मिलकर उसका समाधान किया और समझा कि साथ मिलकर बिताया गया समय सबसे अच्छी याद बन जाता है।"
    if language == "Tamil":
        return f"ஒரு கற்பனைக் கதையில், இந்தக் காட்சியின் கதாபாத்திரங்கள் அமைதியான நேரத்தில் ஒரு சிறிய பிரச்சினையை கவனித்தனர். அவர்கள் ஒன்றாக அதைத் தீர்த்து, சேர்ந்து கழித்த நேரமே சிறந்த நினைவாக மாறும் என்பதை உணர்ந்தனர்."
    if language == "Japanese":
        return f"想像の物語の中で、この場面の登場人物たちは静かな時間に小さな問題を見つけました。力を合わせて解決し、一緒に過ごした時間こそ大切な思い出になると気づきました。"
    return "In a fictional story, the characters notice a small problem during a peaceful moment. They work together to solve it and discover that sharing the moment has created a precious memory."


def build_output_text(caption: str, mode: str, language: str) -> dict:
    narration = None
    if _gemini_ready():
        try:
            narration = ai_utils.generate_story(caption, mode, language)
        except Exception:
            narration = None
    if not narration:
        narration = build_fallback_story(caption, language)

    extra_lines = {
        "English": "Speak clearly, use simple phrases, and describe the people and objects with confidence.",
        "Hindi": "स्पष्ट बोलें, सरल वाक्य बोलें, और लोगों, वस्तुओं और स्थिति को साफ़-साफ़ बताएं।",
        "Tamil": "தெளிவாக பேசுங்கள், எளிய வாக்கியங்களை பயன்படுத்துங்கள், மக்களையும் பொருட்களையும் சூழலையும் தெளிவாக விவரிக்கவும்.",
        "Japanese": "はっきり話し、簡単な文を使って、人や物、状況をわかりやすく説明しましょう。",
    }
    return {"narration": narration, "practice_tip": extra_lines.get(language, extra_lines["English"])}


def localize_image_description(caption: str, language: str) -> str:
    lang_code = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}.get(language, "en")
    try:
        return ai_utils.translate_image_description(caption, lang_code)
    except Exception:
        return caption


def generate_audio_file(text: str, language: str, accent: str, output_name: str = "generated_audio.mp3") -> Optional[str]:
    if not text or not text.strip():
        return None

    lang_map = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}
    accent_tld_map = {
        "US English": "com",
        "UK English": "co.uk",
        "Indian English": "co.in",
        "Hindi (India)": "co.in",
        "Tamil (India)": "co.in",
        "Japanese (Japan)": "co.jp",
    }
    lang = lang_map.get(language, "en")
    tld = accent_tld_map.get(accent, "com")

    try:
        return tts_utils.speak_and_return_path(
            text,
            lang,
            prefer_gtts=True,
            out_path=output_name,
            rate=160,
            tld=tld,
        )
    except Exception:
        pass

    try:
        from gtts import gTTS

        file_path = output_name
        gTTS(text=text, lang=lang, tld=tld, slow=False).save(file_path)
        return file_path
    except Exception:
        return None


def extract_text_from_image(image_bytes: bytes) -> str:
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return ocr_utils.extract_text_from_pil(image)
    except Exception:
        return ""


def get_level_from_score(score: float) -> str:
    if score >= 80:
        return "Advanced"
    if score >= 55:
        return "Intermediate"
    return "Beginner"


def build_quiz_from_caption(caption: str) -> list[dict]:
    return [
        {
            "question": "Which sentence best matches the image description?",
            "options": [caption, "The image is unrelated to this topic.", "Only a blank wall is shown.", "This is a math problem without context."],
            "answer": caption,
        },
        {
            "question": "What is the best communication goal for this image?",
            "options": ["Describe the scene clearly in simple language.", "Ignore the action and focus on the file name.", "Do not mention the people or objects.", "Only speak in numbers."],
            "answer": "Describe the scene clearly in simple language.",
        },
        {
            "question": "Which response shows stronger communication skill?",
            "options": ["I can see people in a warm setting, and they look engaged in the moment.", "The image has no important details.", "There are no visible objects.", "I cannot explain anything."],
            "answer": "I can see people in a warm setting, and they look engaged in the moment.",
        },
    ]


def main() -> None:
    st.set_page_config(page_title="SceneSpeak Communication Coach", page_icon="🗣️")
    st.markdown(css_code, unsafe_allow_html=True)

    if "history" not in st.session_state:
        st.session_state.history = []
    if "adaptive_practice_plan" not in st.session_state:
        st.session_state.adaptive_practice_plan = None
    if "adaptive_practice_plan_context" not in st.session_state:
        st.session_state.adaptive_practice_plan_context = None
    if "japanese_question" not in st.session_state:
        st.session_state.japanese_question = None
    if "japanese_evaluation" not in st.session_state:
        st.session_state.japanese_evaluation = None
    if "main_scene_challenge_questions" not in st.session_state:
        st.session_state.main_scene_challenge_questions = []
    if "main_scene_challenge_index" not in st.session_state:
        st.session_state.main_scene_challenge_index = 0
    if "main_scene_challenge_results" not in st.session_state:
        st.session_state.main_scene_challenge_results = []
    if "main_scene_challenge_evaluation" not in st.session_state:
        st.session_state.main_scene_challenge_evaluation = None
    if "main_scene_challenge_caption" not in st.session_state:
        st.session_state.main_scene_challenge_caption = ""
    if "main_scene_challenge_ocr" not in st.session_state:
        st.session_state.main_scene_challenge_ocr = ""
    if "main_scene_challenge_language" not in st.session_state:
        st.session_state.main_scene_challenge_language = ""
    if "main_scene_challenge_level" not in st.session_state:
        st.session_state.main_scene_challenge_level = ""
    if "main_scene_challenge_id" not in st.session_state:
        st.session_state.main_scene_challenge_id = 0

    st.sidebar.title("Communication Coach")
    language = st.sidebar.selectbox("Language", ["English", "Hindi", "Tamil", "Japanese"], key="sidebar_language")
    accent_options = {
        "English": ["US English", "UK English", "Indian English"],
        "Hindi": ["Hindi (India)"],
        "Tamil": ["Tamil (India)"],
        "Japanese": ["Japanese (Japan)"],
    }
    accent = st.sidebar.selectbox("Voice", accent_options[language])
    focus = st.sidebar.selectbox("Focus area", ["Daily conversation", "Interview speaking", "Travel communication", "School talk", "Friendly dialogue"])
    st.sidebar.page_link("pages/communication_practice.py", label="Open conversation practice")
    st.sidebar.markdown("---")
    st.sidebar.caption("Gemini Pro is used when available for image understanding and adaptive communication coaching.")

    if st.sidebar.button("Clear History"):
        st.session_state.history = []
        st.session_state["last_caption"] = ""
        st.session_state["last_ocr"] = ""
        st.session_state.main_scene_challenge_questions = []
        st.session_state.main_scene_challenge_results = []
        st.session_state.main_scene_challenge_evaluation = None
        st.session_state.main_scene_challenge_index = 0

    st.title("SceneSpeak: AI Image-to-Speech Communication Coach")
    st.caption("Turn one image into a multilingual speaking lesson: understand the scene, listen, answer, and improve.")

    if not _gemini_ready():
        st.warning("Gemini API key not detected. Add GEMINI_API_KEY or GOOGLE_API_KEY to continue with full AI features. The app still works with the built-in fallback description and speech output.")

    uploaded_files = st.file_uploader(
        "Upload one or more images",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        language = st.selectbox(
            "Which language do you need for this image?",
            ["Tamil", "English", "Hindi", "Japanese"],
            index=["Tamil", "English", "Hindi", "Japanese"].index(language),
            key="image_result_language",
        )
        st.caption(f"The image description, speech, and image questions will be provided in {language}.")
        include_ocr = st.checkbox(
            "Also detect text in the image (slower)",
            value=False,
            help="Text detection is optional and can add processing time.",
        )
        include_story = st.checkbox(
            "Generate a story and speech audio (slower)",
            value=False,
            help="Creates a story with Gemini and generates speech audio after the image description.",
        )
        st.subheader("Image Analysis")
        if st.button("Analyze image"):
            with st.spinner("Analyzing uploaded images..."):
                for uploaded in uploaded_files:
                    image_bytes = uploaded.getvalue()
                    caption = ""
                    if _gemini_ready():
                        try:
                            mime_type = getattr(uploaded, "type", "") or "image/jpeg"
                            caption = ai_utils.generate_image_description(
                                image_bytes,
                                uploaded.name,
                                mime_type,
                                language,
                            )
                        except Exception:
                            caption = fallback_image_caption(uploaded.name)
                    else:
                        caption = fallback_image_caption(uploaded.name)

                    ocr_text = extract_text_from_image(image_bytes) if include_ocr else ""
                    localized_caption = caption
                    narration = ""
                    tip = ""
                    audio_path = None
                    if include_story:
                        result = build_output_text(caption, "Original Story", language)
                        narration = result["narration"]
                        tip = result["practice_tip"]
                        audio_path = generate_audio_file(
                            narration,
                            language,
                            accent,
                            f"{uploaded.name}_speech.mp3",
                        )

                    st.subheader(f"Result: {uploaded.name}")
                    st.info(localized_caption)
                    if include_story:
                        st.write("**Speech audio**")
                        if audio_path:
                            st.audio(audio_path)
                        else:
                            st.warning("Speech generation was unavailable for this output.")

                        st.write("**Fictional story inspired by the image**")
                        st.write(narration)

                        st.write("**Practice tip**")
                        st.write(tip)

                    if ocr_text:
                        with st.expander("Detected text in the image"):
                            st.write(ocr_text)

                    st.session_state.history.append({
                        "image": uploaded.name,
                        "caption": localized_caption,
                        "caption_english": caption,
                        "narration": narration,
                        "language": language,
                        "accent": accent,
                        "focus": focus,
                        "ocr_text": ocr_text,
                    })

                    st.session_state["last_caption"] = caption
                    st.session_state["last_localized_caption"] = localized_caption
                    st.session_state["last_ocr"] = ocr_text

    if st.session_state.get("last_caption"):
        st.markdown("---")
        st.subheader(f"{language} questions about the image")
        st.caption("These questions are generated from the visible context of your uploaded image.")
        if st.button("Generate questions from this image"):
            language_code = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}[language]
            with st.spinner("Creating image-context questions..."):
                st.session_state.image_context_questions = ai_utils.generate_image_questions(
                    st.session_state["last_caption"],
                    st.session_state.get("last_ocr", ""),
                    language_code,
                    "Beginner",
                )
        for index, image_question in enumerate(st.session_state.get("image_context_questions", []), start=1):
            st.write(f"{index}. {image_question['question']}")
            st.caption(f"English meaning: {image_question['translation']}")

        st.markdown("---")
        st.subheader("SceneSpeak: three-round image challenge")
        st.caption(
            "Turn this image into a speaking challenge: observe visible details, explain your idea "
            "using clues, then imagine what could happen next."
        )
        scene_level = st.selectbox(
            "Challenge level",
            ["Beginner", "Intermediate", "Advanced"],
            key="main_scene_challenge_level_selector",
        )
        if st.button("Start / restart SceneSpeak challenge", key="start_main_scene_challenge"):
            scene_language_code = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}[language]
            with st.spinner("Creating three image-based speaking rounds..."):
                st.session_state.main_scene_challenge_questions = ai_utils.generate_scene_challenge_questions(
                    st.session_state["last_caption"],
                    st.session_state.get("last_ocr", ""),
                    scene_language_code,
                    scene_level,
                )
            st.session_state.main_scene_challenge_caption = st.session_state["last_caption"]
            st.session_state.main_scene_challenge_ocr = st.session_state.get("last_ocr", "")
            st.session_state.main_scene_challenge_language = language
            st.session_state.main_scene_challenge_level = scene_level
            st.session_state.main_scene_challenge_index = 0
            st.session_state.main_scene_challenge_results = []
            st.session_state.main_scene_challenge_evaluation = None
            st.session_state.main_scene_challenge_id += 1

        challenge_is_stale = bool(
            st.session_state.main_scene_challenge_questions
            and (
                st.session_state.main_scene_challenge_caption != st.session_state["last_caption"]
                or st.session_state.main_scene_challenge_ocr != st.session_state.get("last_ocr", "")
                or st.session_state.main_scene_challenge_language != language
                or st.session_state.main_scene_challenge_level != scene_level
            )
        )
        if challenge_is_stale:
            st.info("The image, language, or level changed. Start a new challenge to refresh its questions.")

        if st.session_state.main_scene_challenge_questions and not challenge_is_stale:
            rounds = st.session_state.main_scene_challenge_questions
            round_index = st.session_state.main_scene_challenge_index
            if round_index < len(rounds):
                challenge_round = rounds[round_index]
                challenge_id = st.session_state.main_scene_challenge_id
                st.progress(round_index / len(rounds))
                st.caption(f"Round {round_index + 1} of {len(rounds)} · {challenge_round['stage']}")
                st.info(f"{challenge_round['question']}\n\nEnglish meaning: {challenge_round['translation']}")
                st.caption(f"Speaking goal: {challenge_round['goal']}")

                question_audio_key = f"main_scene_question_audio_{challenge_id}_{round_index}"
                if question_audio_key not in st.session_state:
                    st.session_state[question_audio_key] = generate_audio_file(
                        challenge_round["question"],
                        language,
                        accent,
                        f"scene_challenge_{challenge_id}_{round_index}.mp3",
                    )
                if st.session_state[question_audio_key]:
                    st.audio(st.session_state[question_audio_key])

                recorded_answer = st.audio_input(
                    "Record your answer",
                    key=f"main_scene_audio_{challenge_id}_{round_index}",
                    help="Allow microphone access, or upload a recording below.",
                )
                uploaded_answer = st.file_uploader(
                    "Or upload a recorded answer",
                    type=["wav", "mp3", "m4a", "ogg", "webm"],
                    key=f"main_scene_upload_{challenge_id}_{round_index}",
                )

                current_evaluation = st.session_state.main_scene_challenge_evaluation
                if not current_evaluation or current_evaluation.get("error"):
                    if st.button("Evaluate this round", key=f"evaluate_main_scene_{challenge_id}_{round_index}"):
                        selected_audio = recorded_answer or uploaded_answer
                        if selected_audio is None:
                            st.warning("Record or upload an answer before evaluation.")
                        else:
                            with st.spinner("Listening and reviewing your answer..."):
                                scene_language_code = {
                                    "English": "en",
                                    "Hindi": "hi",
                                    "Tamil": "ta",
                                    "Japanese": "ja",
                                }[language]
                                current_evaluation = ai_utils.evaluate_audio_answer(
                                    scene_language_code,
                                    challenge_round["question"],
                                    selected_audio.getvalue(),
                                    getattr(selected_audio, "type", "audio/wav"),
                                    scene_level,
                                )
                                st.session_state.main_scene_challenge_evaluation = current_evaluation
                                if not current_evaluation.get("error"):
                                    st.session_state.main_scene_challenge_results.append({
                                        "stage": challenge_round["stage"],
                                        "score": max(0, min(100, int(current_evaluation.get("score", 0)))),
                                        "transcript": current_evaluation.get("transcript", ""),
                                    })

                current_evaluation = st.session_state.main_scene_challenge_evaluation
                if current_evaluation:
                    score = max(0, min(100, int(current_evaluation.get("score", 0))))
                    if current_evaluation.get("error"):
                        st.warning(f"Audio evaluation was not completed: {current_evaluation['error']}")
                    else:
                        st.success(f"{score}/100 | {current_evaluation.get('level', 'Beginner')}")
                    st.write(current_evaluation.get("feedback", ""))
                    if current_evaluation.get("transcript"):
                        st.markdown(f"**What we heard:** {current_evaluation['transcript']}")
                    if current_evaluation.get("corrected_answer"):
                        st.markdown(f"**Suggested answer:** {current_evaluation['corrected_answer']}")
                    if current_evaluation.get("corrections"):
                        st.markdown("**Corrections**")
                        for correction in current_evaluation["corrections"]:
                            st.write(
                                f"{correction.get('original', '')} → {correction.get('correction', '')}: "
                                f"{correction.get('explanation', '')}"
                            )
                    if current_evaluation.get("vocabulary"):
                        st.markdown("**Recommended vocabulary**")
                        for word in current_evaluation["vocabulary"]:
                            st.write(
                                f"**{word.get('word', '')}** ({word.get('reading', '')}) — "
                                f"{word.get('meaning', '')}"
                            )
                    if current_evaluation.get("pronunciation"):
                        st.markdown(f"**Pronunciation practice:** {current_evaluation['pronunciation']}")
                    if current_evaluation.get("usage"):
                        st.markdown(f"**When to use it:** {current_evaluation['usage']}")

                    if not current_evaluation.get("error"):
                        next_label = "Continue to next round" if round_index + 1 < len(rounds) else "Finish challenge"
                        if st.button(next_label, key=f"continue_main_scene_{challenge_id}_{round_index}"):
                            st.session_state.main_scene_challenge_index += 1
                            st.session_state.main_scene_challenge_evaluation = None
                            st.rerun()
            else:
                results = st.session_state.main_scene_challenge_results
                if results:
                    average_score = round(sum(result["score"] for result in results) / len(results))
                    weakest_round = min(results, key=lambda result: result["score"])
                    st.progress(1.0)
                    st.success(f"Challenge complete · Average score: {average_score}/100")
                    st.markdown("**Round-by-round recap**")
                    for result in results:
                        st.write(f"**{result['stage']} · {result['score']}/100**")
                        if result["transcript"]:
                            st.caption(f"What we heard: {result['transcript']}")
                    st.info(
                        f"Suggested next focus: practise **{weakest_round['stage'].lower()}** "
                        f"responses and build on your {weakest_round['score']}/100 result."
                    )
                else:
                    st.warning("No round was successfully evaluated. Restart the challenge and try again.")

    st.markdown("---")
    st.subheader(f"{language} conversation practice")
    st.caption(f"The AI asks a {language} question. Answer naturally in {language}, then review your corrections, pronunciation, and word usage.")
    practice_level = st.selectbox("Practice level", ["Beginner", "Intermediate", "Advanced"], key="japanese_level")
    practice_focus = st.selectbox(
        "Conversation topic",
        ["Daily conversation", "Self introduction", "Travel", "Shopping", "School and work"],
        key="japanese_focus",
    )

    if st.button(f"Ask me a {language} question"):
        with st.spinner(f"Creating a {language} conversation question..."):
            language_code = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}[language]
            st.session_state.japanese_question = ai_utils.generate_language_question(language_code, practice_level, practice_focus)
            st.session_state.japanese_language = language
            st.session_state.japanese_evaluation = None

    question_data = st.session_state.get("japanese_question")
    if question_data:
        practice_language = st.session_state.get("japanese_language", language)
        practice_accent = {
            "English": "US English",
            "Hindi": "Hindi (India)",
            "Tamil": "Tamil (India)",
            "Japanese": "Japanese (Japan)",
        }[practice_language]
        st.info(f"質問: {question_data['question']}\n\nEnglish meaning: {question_data['translation']}")
        question_audio = generate_audio_file(
            question_data["question"],
            practice_language,
            practice_accent,
            "conversation_question.mp3",
        )
        if question_audio:
            st.audio(question_audio)

        answer = st.text_area(
            f"Your answer in {practice_language}",
            placeholder="Type your answer here",
            height=120,
            key="japanese_answer",
        )
        if st.button(f"Evaluate my {practice_language} answer"):
            if not answer.strip():
                st.warning("Please enter an answer in Japanese before evaluating it.")
            else:
                with st.spinner("Evaluating meaning, grammar, and naturalness..."):
                    language_code = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}[practice_language]
                    st.session_state.japanese_evaluation = ai_utils.evaluate_language_answer(
                        language_code,
                        question_data["question"],
                        answer.strip(),
                        practice_level,
                    )

    evaluation = st.session_state.get("japanese_evaluation")
    if evaluation:
        score = max(0, min(100, int(evaluation.get("score", 0))))
        st.success(f"Score: {score}/100 | Level: {evaluation.get('level', 'Beginner')}")
        st.write(evaluation.get("feedback", ""))
        st.markdown(f"**Corrected answer:** {evaluation.get('corrected_answer', '')}")

        corrections = evaluation.get("corrections", [])
        if corrections:
            st.markdown("**Corrections**")
            for correction in corrections:
                st.write(
                    f"{correction.get('original', '')} -> {correction.get('correction', '')}: "
                    f"{correction.get('explanation', '')}"
                )

        vocabulary = evaluation.get("vocabulary", [])
        if vocabulary:
            st.markdown("**Recommended words**")
            for word in vocabulary:
                st.write(
                    f"**{word.get('word', '')}** ({word.get('reading', '')}) - {word.get('meaning', '')}\n\n"
                    f"Pronunciation: {word.get('pronunciation', '')}\n\n"
                    f"Usage: {word.get('usage_example', '')}"
                )

        st.markdown(f"**Pronunciation practice:** {evaluation.get('pronunciation', '')}")
        st.markdown(f"**When to use it:** {evaluation.get('usage', '')}")
        corrected_audio = generate_audio_file(
            evaluation.get("corrected_answer", ""),
            practice_language,
            practice_accent,
            "corrected_conversation_answer.mp3",
        )
        if corrected_audio:
            st.caption("Listen to the corrected answer")
            st.audio(corrected_audio)

        practice_plan = ai_utils.generate_practice_plan("Advanced" if score >= 80 else "Intermediate" if score >= 55 else "Beginner", practice_language, score)
        st.markdown("**Next practice recommendation**")
        st.write(practice_plan)

    st.markdown("---")
    st.subheader("Adaptive topics for improvement")
    if st.session_state.history:
        latest = st.session_state.history[-1]
        score_sample = 62
        if latest.get("caption"):
            score_sample = 70 if "people" in latest["caption"].lower() else 55
        level = get_level_from_score(score_sample)
        plan_context = (latest.get("caption", ""), language, level, score_sample)
        if st.button("Generate adaptive practice recommendations"):
            st.session_state.adaptive_practice_plan = ai_utils.generate_practice_plan(
                level,
                language,
                score_sample,
            )
            st.session_state.adaptive_practice_plan_context = plan_context
        if st.session_state.adaptive_practice_plan_context == plan_context:
            st.write(st.session_state.adaptive_practice_plan)
    else:
        st.write("Start with one image to generate a communication practice plan based on learner progress.")

    st.markdown("---")
    st.subheader("Recent results")
    if st.session_state.history:
        for item in reversed(st.session_state.history):
            with st.container(border=True):
                st.write(f"**Image:** {item['image']}")
                st.write(f"**Language:** {item['language']}")
                st.write(f"**Accent:** {item['accent']}")
                st.write(f"**Caption:** {item['caption']}")
                if item["narration"]:
                    st.write(item["narration"])
    else:
        st.write("No recent results yet.")

    st.markdown("---")
    st.subheader("Ask about the image")
    question = st.text_input("Type a question about the uploaded image", key="question_box")
    if st.button("Ask Gemini") and question:
        caption = st.session_state.get("last_caption") or "No image description yet."
        ocr_text = st.session_state.get("last_ocr", "")
        try:
            answer = ai_utils.answer_question_from_context(caption, ocr_text, question)
            st.write(answer)
            audio_answer = generate_audio_file(answer, language, accent, "answer_audio.mp3")
            if audio_answer:
                st.audio(audio_answer)
        except Exception as exc:
            st.error(f"Gemini Q&A failed: {exc}")


if __name__ == "__main__":
    main()

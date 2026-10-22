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
    lang_code = {"English": "en", "Hindi": "hi", "Tamil": "ta", "Japanese": "ja"}.get(language, "en")
    narration = None
    if _gemini_ready():
        try:
            narration = ai_utils.generate_story(caption, mode, language)
        except Exception:
            narration = None
    if not narration:
        narration = build_fallback_story(caption, language)

    if language != "English":
        try:
            narration = ai_utils.translate_text(narration, lang_code)
        except Exception:
            pass

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
    st.set_page_config(page_title="Communication Coach with Gemini", page_icon="🗣️")
    st.markdown(css_code, unsafe_allow_html=True)

    if "history" not in st.session_state:
        st.session_state.history = []
    if "japanese_question" not in st.session_state:
        st.session_state.japanese_question = None
    if "japanese_evaluation" not in st.session_state:
        st.session_state.japanese_evaluation = None

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

    st.title("AI Image-to-Speech Communication Coach")
    st.caption("Upload an image, get a clear description, listen to the speech in the selected accent, and improve communication with adaptive practice topics.")

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
        st.subheader("Image Analysis")
        if st.button("Generate description and speech"):
            with st.spinner("Analyzing image and preparing speech output..."):
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

                    ocr_text = extract_text_from_image(image_bytes)
                    localized_caption = caption
                    result = build_output_text(caption, "Original Story", language)
                    narration = result["narration"]
                    tip = result["practice_tip"]

                    audio_path = generate_audio_file(narration, language, accent, f"{uploaded.name}_speech.mp3")

                    st.subheader(f"Result: {uploaded.name}")
                    st.info(localized_caption)
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
        plan = ai_utils.generate_practice_plan(level, language, score_sample)
        st.write(plan)
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
                st.write(item['narration'])
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

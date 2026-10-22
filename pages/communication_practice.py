import streamlit as st

from utils import ai_utils
from utils import tts as tts_utils
from utils.custom import css_code


LANGUAGES = {
    "English": {"code": "en", "voice": "US English", "tld": "com"},
    "Hindi": {"code": "hi", "voice": "Hindi (India)", "tld": "co.in"},
    "Tamil": {"code": "ta", "voice": "Tamil (India)", "tld": "co.in"},
    "Japanese": {"code": "ja", "voice": "Japanese (Japan)", "tld": "co.jp"},
}

UI_TEXT = {
    "English": {
        "title": "Conversation practice",
        "caption": "Record your answer. The AI will transcribe and evaluate your speaking.",
        "level": "Practice level",
        "topic": "Conversation topic",
        "ask": "Ask me a question",
        "answer": "Record your answer",
        "evaluate": "Evaluate my answer",
        "meaning": "English meaning",
        "transcript": "What we heard",
        "correction": "Corrected answer",
        "vocabulary": "Recommended words",
        "pronunciation": "Pronunciation practice",
        "usage": "When to use it",
        "next": "Next practice recommendation",
        "empty": "Record an answer before evaluating it.",
    },
    "Hindi": {
        "title": "बातचीत का अभ्यास",
        "caption": "अपना उत्तर रिकॉर्ड करें। AI आपकी आवाज़ को लिखकर उसका मूल्यांकन करेगा।",
        "level": "अभ्यास स्तर",
        "topic": "बातचीत का विषय",
        "ask": "मुझसे एक प्रश्न पूछें",
        "answer": "अपना उत्तर रिकॉर्ड करें",
        "evaluate": "मेरे उत्तर का मूल्यांकन करें",
        "meaning": "अंग्रेज़ी अर्थ",
        "transcript": "हमने यह सुना",
        "correction": "सही उत्तर",
        "vocabulary": "सुझाए गए शब्द",
        "pronunciation": "उच्चारण अभ्यास",
        "usage": "इसका उपयोग कब करें",
        "next": "अगला अभ्यास सुझाव",
        "empty": "मूल्यांकन से पहले अपना उत्तर रिकॉर्ड करें।",
    },
    "Tamil": {
        "title": "உரையாடல் பயிற்சி",
        "caption": "உங்கள் பதிலை பதிவு செய்யுங்கள். AI உங்கள் பேச்சை எழுதி மதிப்பீடு செய்யும்.",
        "level": "பயிற்சி நிலை",
        "topic": "உரையாடல் தலைப்பு",
        "ask": "என்னிடம் ஒரு கேள்வி கேளுங்கள்",
        "answer": "உங்கள் பதிலை பதிவு செய்யுங்கள்",
        "evaluate": "என் பதிலை மதிப்பீடு செய்யுங்கள்",
        "meaning": "ஆங்கில அர்த்தம்",
        "transcript": "நாங்கள் கேட்டது",
        "correction": "சரியான பதில்",
        "vocabulary": "பரிந்துரைக்கப்பட்ட சொற்கள்",
        "pronunciation": "உச்சரிப்பு பயிற்சி",
        "usage": "எப்போது பயன்படுத்துவது",
        "next": "அடுத்த பயிற்சி பரிந்துரை",
        "empty": "மதிப்பீட்டிற்கு முன் உங்கள் பதிலை பதிவு செய்யுங்கள்.",
    },
    "Japanese": {
        "title": "会話練習",
        "caption": "答えを録音してください。AIが音声を書き起こして評価します。",
        "level": "練習レベル",
        "topic": "会話のテーマ",
        "ask": "質問をしてください",
        "answer": "答えを録音してください",
        "evaluate": "答えを評価する",
        "meaning": "英語の意味",
        "transcript": "聞き取った答え",
        "correction": "正しい答え",
        "vocabulary": "おすすめの言葉",
        "pronunciation": "発音練習",
        "usage": "使う場面",
        "next": "次の練習のおすすめ",
        "empty": "評価する前に答えを録音してください。",
    },
}


def generate_audio(text: str, language: str, output_name: str):
    if not text or not text.strip():
        return None
    settings = LANGUAGES[language]
    try:
        return tts_utils.speak_and_return_path(
            text,
            settings["code"],
            prefer_gtts=True,
            out_path=output_name,
            rate=160,
            tld=settings["tld"],
        )
    except Exception:
        return None


def render_evaluation(evaluation: dict, language: str, text: dict) -> None:
    score = max(0, min(100, int(evaluation.get("score", 0))))
    if evaluation.get("error"):
        st.warning(f"Audio evaluation was not completed: {evaluation['error']}")
    else:
        st.success(f"{score}/100 | {evaluation.get('level', 'Beginner')}")
    st.write(evaluation.get("feedback", ""))
    st.markdown(f"**{text['transcript']}:** {evaluation.get('transcript', '')}")
    st.markdown(f"**{text['correction']}:** {evaluation.get('corrected_answer', '')}")

    for correction in evaluation.get("corrections", []):
        st.write(
            f"{correction.get('original', '')} -> {correction.get('correction', '')}: "
            f"{correction.get('explanation', '')}"
        )

    vocabulary = evaluation.get("vocabulary", [])
    if vocabulary:
        st.markdown(f"**{text['vocabulary']}**")
        for word in vocabulary:
            st.write(
                f"**{word.get('word', '')}** ({word.get('reading', '')}) - {word.get('meaning', '')}\n\n"
                f"Pronunciation: {word.get('pronunciation', '')}\n\n"
                f"Usage: {word.get('usage_example', '')}"
            )

    st.markdown(f"**{text['pronunciation']}:** {evaluation.get('pronunciation', '')}")
    st.markdown(f"**{text['usage']}:** {evaluation.get('usage', '')}")
    corrected_audio = generate_audio(evaluation.get("corrected_answer", ""), language, "corrected_answer.mp3")
    if corrected_audio:
        st.audio(corrected_audio)

    level = "Advanced" if score >= 80 else "Intermediate" if score >= 55 else "Beginner"
    st.markdown(f"**{text['next']}**")
    st.write(ai_utils.generate_practice_plan(level, language, score))


st.set_page_config(page_title="Conversation Practice", page_icon=":material/forum:")
st.markdown(css_code, unsafe_allow_html=True)

language = st.selectbox("Language / भाषा / மொழி / 言語", list(LANGUAGES), key="practice_page_language")
text = UI_TEXT[language]
st.title(text["title"])
st.caption(text["caption"])

level = st.selectbox(text["level"], ["Beginner", "Intermediate", "Advanced"], key="practice_page_level")
focus = st.selectbox(
    text["topic"],
    ["Daily conversation", "Self introduction", "Travel", "Shopping", "School and work"],
    key="practice_page_focus",
)

if "practice_page_question" not in st.session_state:
    st.session_state.practice_page_question = None
if "practice_page_evaluation" not in st.session_state:
    st.session_state.practice_page_evaluation = None
if "image_questions" not in st.session_state:
    st.session_state.image_questions = []
if "image_question_index" not in st.session_state:
    st.session_state.image_question_index = 0

if st.session_state.get("last_caption"):
    st.subheader("Image context speaking practice")
    st.caption("Answer questions about your uploaded image. The AI checks whether your spoken answer matches the visible context.")
    if st.button("Ask questions about my image"):
        with st.spinner("Creating questions from the image..."):
            settings = LANGUAGES[language]
            st.session_state.image_questions = ai_utils.generate_image_questions(
                st.session_state["last_caption"],
                st.session_state.get("last_ocr", ""),
                settings["code"],
                level,
            )
            st.session_state.image_question_index = 0
            st.session_state.practice_page_evaluation = None

    image_questions = st.session_state.image_questions
    if image_questions:
        image_question = image_questions[st.session_state.image_question_index % len(image_questions)]
        st.info(f"{image_question['question']}\n\n{text['meaning']}: {image_question['translation']}")
        image_question_audio = generate_audio(image_question["question"], language, "image_question.mp3")
        if image_question_audio:
            st.audio(image_question_audio)
        image_audio_answer = st.audio_input(
            text["answer"],
            key="image_audio_answer",
            help="Allow microphone access, or use the audio-file upload below if recording is unavailable.",
        )
        image_audio_upload = st.file_uploader(
            "Or upload a recorded answer",
            type=["wav", "mp3", "m4a", "ogg", "webm"],
            key="image_audio_upload",
        )
        if st.button(text["evaluate"], key="evaluate_image_answer"):
            selected_audio = image_audio_answer or image_audio_upload
            if selected_audio is None:
                st.warning(text["empty"])
            else:
                with st.spinner("..."):
                    settings = LANGUAGES[language]
                    st.session_state.practice_page_evaluation = ai_utils.evaluate_audio_answer(
                        settings["code"],
                        image_question["question"],
                        selected_audio.getvalue(),
                        getattr(selected_audio, "type", "audio/wav"),
                        level,
                    )
        if st.button("Next image question", key="next_image_question"):
            st.session_state.image_question_index += 1
            st.session_state.practice_page_evaluation = None
            st.rerun()

if st.button(text["ask"], type="primary"):
    with st.spinner("..."):
        settings = LANGUAGES[language]
        st.session_state.practice_page_question = ai_utils.generate_language_question(settings["code"], level, focus)
        st.session_state.practice_page_evaluation = None

question = st.session_state.practice_page_question
if question:
    st.info(f"{question['question']}\n\n{text['meaning']}: {question['translation']}")
    question_audio = generate_audio(question["question"], language, "practice_question.mp3")
    if question_audio:
        st.audio(question_audio)

    audio_answer = st.audio_input(
        text["answer"],
        key="conversation_audio_answer",
        help="Allow microphone access, or use the audio-file upload below if recording is unavailable.",
    )
    audio_upload = st.file_uploader(
        "Or upload a recorded answer",
        type=["wav", "mp3", "m4a", "ogg", "webm"],
        key="conversation_audio_upload",
    )
    if st.button(text["evaluate"]):
        selected_audio = audio_answer or audio_upload
        if selected_audio is None:
            st.warning(text["empty"])
        else:
            with st.spinner("..."):
                settings = LANGUAGES[language]
                st.session_state.practice_page_evaluation = ai_utils.evaluate_audio_answer(
                    settings["code"],
                    question["question"],
                    selected_audio.getvalue(),
                    getattr(selected_audio, "type", "audio/wav"),
                    level,
                )

if st.session_state.practice_page_evaluation:
    render_evaluation(st.session_state.practice_page_evaluation, language, text)
else:
    st.info(text["ask"])

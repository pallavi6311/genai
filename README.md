# SceneSpeak: AI Image-to-Speech Communication Coach

A Streamlit application that helps people practice communication by turning
uploaded images into accurate visual descriptions, translated narration, and
spoken audio. It is designed for learners who need support communicating in
multiple languages.

## Features

- Gemini image understanding that identifies visible people, animals, objects,
  colors, positions, actions, setting, and readable text.
- Quick image descriptions by default, with OCR, story/audio generation, and
  adaptive recommendations available on demand.
- Image-context questions generated from the uploaded image, so learners can
  explain what is visible and what is happening in the scene.
- Image Q&A sends the analyzed image itself, along with its description and
  detected text, so answers address the specific question instead of repeating
  the image caption.
- SceneSpeak three-round challenge: learners observe visible details, explain
  an interpretation using visual clues, then imagine a possible continuation.
  Each round uses spoken-answer feedback and contributes to a session recap.
- Grounded descriptions that avoid guessing names, identities, locations,
  brands, or intentions when the image does not provide enough evidence.
- Narration and translation in English, Hindi, Tamil, and Japanese.
- Language-aware speech voices:
  - English: US, UK, or Indian English
  - Hindi: India
  - Tamil: India
  - Japanese: Japan
- OCR for readable text inside uploaded images.
- AI conversation practice in English, Hindi, Tamil, and Japanese with
  Beginner, Intermediate, and Advanced levels.
- Free-form answers evaluated for meaning, grammar, politeness, and
  naturalness.
- Corrected answer with score, feedback, recommended words, readings,
  pronunciation guidance, and usage examples.
- Spoken questions and corrected answer audio in the selected language.
- Dedicated Streamlit conversation-practice page with microphone recording;
  learners answer by voice instead of typing.
- Spoken-answer evaluation in every supported language, including transcription,
  grammar and meaning mistakes, pronunciation advice, corrected speech, and
  usage recommendations.
- Separate speaking scores for grammar, pronunciation, fluency, and answer
  relevance, plus a current level based on the overall score.
- A personalized 7-day speaking schedule based on the latest score and feedback,
  with a built-in schedule available when Gemini is unavailable.
- Gemini-generated practice topics based on the learner's actual score.
- Built-in fallback text and offline `pyttsx3` speech when online services are
  unavailable.
- No dataset upload workflow and no image-dimension output.

## Project structure

```text
.
|-- app.py                 Streamlit interface and application flow
|-- utils/
|   |-- ai_utils.py        Gemini image analysis, translation, and coaching
|   |-- custom.py          Application styling
|   |-- ocr.py             OCR helper
|   `-- tts.py             gTTS and pyttsx3 speech helper
|-- requirements.txt
|-- .env                   Local API configuration; do not commit this file
|-- LICENSE
`-- README.md
```

## Requirements

- Python 3.10 or newer
- Internet access for Gemini and gTTS features
- A Gemini API key from Google AI Studio
- Tesseract OCR installed locally if OCR is required

## Installation on Windows

From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run the app directly with the virtual
environment Python instead:

```powershell
& .\.venv\Scripts\python.exe -m streamlit run app.py
```

## Configure Gemini

Create a file named `.env` in the same directory as `app.py`:

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
```

Never commit `.env` or share the API key. The app also recognizes
`GOOGLE_API_KEY` and `GENAI_API_KEY` if one of those names is already used in
your environment.

## Run

```powershell
& .\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open the local URL shown by Streamlit, normally:

```text
http://localhost:8501
```

## Deploy to Render

1. Push this project to a GitHub repository.
2. In Render, choose **New > Blueprint** and connect that repository. Render
   will use `render.yaml` and build the app from `Dockerfile`.
3. Add `GEMINI_API_KEY` as a secret environment variable when prompted. The
   app can start without it, but Gemini-powered features will use their
   documented fallback behavior.
4. Deploy the Blueprint. Render assigns the public URL after the first
   deployment completes.

The Docker image installs Tesseract OCR and eSpeak for the app's Linux
deployment. Local `.env` files, generated audio, and temporary files are
excluded from the Git and Docker build contexts.

## How to use

1. Choose a language and matching voice in the sidebar.
2. Upload one or more PNG, JPG, or JPEG images.
3. Select **Analyze image** for a quick visual description.
4. Enable OCR or story-and-speech generation before analyzing if you need those
   optional, slower features.
5. Open conversation practice and choose a level and topic.
6. Ask the AI for a question, record your answer with the microphone (or upload
  an audio recording), and submit it.
7. Review your overall score and current level, grammar and pronunciation
  subscores, transcript, correction, vocabulary, and pronunciation guidance.
8. Follow the personalized 7-day speaking schedule and record another answer
  to track improvement.
9. Optionally generate adaptive practice recommendations on the main page.

The **SceneSpeak** challenge is available directly below the image questions on
the main page after an image description has been generated. Choose a level,
then practise in three stages: Observe, Explain, and Imagine. Record or upload
an answer for each stage, then review the round scores and suggested focus.
The **Open conversation practice** page in the sidebar remains available for
standalone conversation and image-context speaking practice. Both pages support
English, Hindi, Tamil, and Japanese.

## Fallback behavior

- Without a Gemini key, the app remains available but cannot produce a true
  visual analysis. It displays a fallback message instead of inventing image
  details.
- Without internet access, gTTS may fail and the app tries local `pyttsx3`
  speech. Local fallback voices depend on the voices installed in Windows.
- If Tesseract is unavailable, the main image description and speech still work;
  only OCR is unavailable.

## License

Distributed under the MIT License. See `LICENSE`.

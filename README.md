AI Interview Assistant & Interview Copilot

License: http://www.apache.org/licenses/

AI-Assistant is an open-source, real-time AI interview assistant and interview copilot for technical and behavioral interviews. It runs as a small floating desktop overlay that can listen to a live interview call, read a question straight off your screen, or take dictation from your own voice — then draws on your resume and a few live web search results to suggest an answer, using the LLM provider of your choice.

<!-- Add a screenshot or short screen-recording GIF of the overlay in action here — it helps both visitors deciding to try the project and Google Images traffic. -->


Features
Multiple LLM providers — Groq (llama-3.3-70b-versatile by default, generous free tier), a fully local and free Ollama model, Mistral AI, or OpenAI. Switch providers from the settings panel or a single .env variable. or from the Ui can pass
Live meeting audio — listens to your system/loopback audio (whatever's playing from Zoom, Google Meet, Microsoft Teams, etc.) and transcribes it automatically in real time, a few seconds at a time.
Voice dictation — click the mic button to ask a question out loud instead of typing it.
Screen understanding — the "Analyse Screen" button captures a screenshot read and extract the question directly, with no separate OCR step.
Resume-aware answers — upload a PDF or DOCX resume once, and answers can reference your real background and experience.
Live web search grounding — pulls a few DuckDuckGo results (no API key needed) into the prompt so answers can reflect current information.
Stealth overlay, on by default — an always-on-top, semi-transparent window that, on Windows 10 (build 2004+) and 11, is excluded from screen-share and screen-recording tools (Zoom, Teams, Google Meet, OBS) via the Windows SetWindowDisplayAffinity API. Toggle the whole window with the global hotkey Ctrl+Shift+Space.

How It Works
The app opens as a small, floating, always-on-top window (hidden from screen-share by default on Windows).
It picks up a question three ways: transcribing your meeting's audio, vision-based screen reading, or your own typed/dictated input.
That question is combined with your resume text and a short web search summary into one prompt.
The prompt is sent to whichever LLM provider you've configured —ex:  Groq, OpenAI, Mistral, or a local Ollama model.
The model's answer is displayed back in the overlay.
Project Structure

File	Purpose
main.py / __main__.py	App entry point and PyQt5 GUI (the overlay window itself)
ai_client.py	Unified chat client across Groq, Ollama, Mistral, and OpenAI-compatible endpoints
meeting_listener.py	Real-time loopback audio capture and transcription of meeting audio
voice_client.py	Background microphone listener for voice dictation
image_client.py	Screenshot capture and vision-based screen reading
resume_client.py	Parses an uploaded PDF/DOCX/TXT resume into plain text
search_client.py	Lightweight DuckDuckGo web search for grounding answers
stealth.py	Hides the overlay window from screen-capture and screen-share tools on Windows
run.bat	Sets up a virtual environment, installs dependencies, and launches the app
Requirements
Windows 10 (build 2004 or later) or Windows 11. Meeting-audio loopback capture (pyaudiowpatch) and the stealth overlay (pywin32) both rely on Windows-only APIs, so macOS/Linux aren't supported yet. On unsupported Windows builds, stealth mode simply fails to activate and the window stays visible.
Python 3.10+ (recommended)
At least one of: a Groq API key (free tier), an OpenAI API key, a Mistral AI API key, or a local Ollama install
A microphone (for voice dictation) and a working audio-output/loopback device (for meeting-audio capture)
Installation
bash
git clone https://github.com/Yashwanthgowda1/AI-Assistant.git
cd AI-Assistant
pip install -r requirements.txt

Copy the example environment file and fill in at least one API key:

bat
copy .env.example .env
Configuration

Set these in your .env file:

Variable	Description
GROQ_API_KEY	API key from console.groq.com
MISTRAL_API_KEY	API key from Mistral AI — also used for screen/vision analysis
OPENAI_API_KEY	API key from OpenAI
AI_PROVIDER	groq, ollama, mistral, or openai
AI_MODEL	Model name for the selected provider (default: llama-3.3-70b-versatile)
Usage
bat
run.bat

This creates a virtual environment, installs dependencies, and launches the app. The window is hidden from screen-share by default — press Ctrl+Shift+Space to show or hide it.

If your environment is already set up, you can also run:

bash
python main.py

From the app itself:

Type a question, or click the mic button to dictate it.
Click Analyse Screen to have it read a question straight off your screen.
Click Upload Resume once so answers can reference your background.
Toggle Meeting to transcribe your call's audio automatically.
Use the settings panel to pick a provider/model or update API keys.
Use Cases
Rehearsing answers to common technical and behavioral interview questions before the real thing.
Getting unstuck on a live coding or take-home question by having the screen read automatically.
Practicing how to talk through your own resume and experience out loud.
Real-time support during a live video interview on Zoom, Google Meet, or Microsoft Teams.
Responsible Use

This is built to sit on top of a real video call, with screen-share hiding on by default, so it's worth being deliberate about when and how you use it. Many employers and interview platforms have explicit policies against undisclosed AI assistance during live interviews, and some video-conferencing tools are starting to detect overlays like this one — using it live without disclosure can violate those policies or a candidate agreement. It's on you to know the rules of whatever process you're in. The software itself is provided as-is, with no warranty.

Contributing

Issues and pull requests are welcome. macOS/Linux support, additional LLM or transcription providers, and general bug fixes are all good places to start — open an issue first if you're planning something larger.

License

Licensed under the GNU Affero General Public License v3.0 (AGPL-3.0) — see LICENSE. In short: if you modify this project and run it as a network service for others, you must make your modified source available to that service's users.

If this is useful, a ⭐ on the repo helps other people searching for an AI interview assistant find it too.

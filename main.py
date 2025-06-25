import streamlit as st
import asyncio
import edge_tts
import tempfile
import os
from pydub import AudioSegment
import json

# 🎙️ Voice options
VOICES = {
    "Jenny (US, Female)": "en-US-JennyNeural",
    "Aria (US, Female)": "en-US-AriaNeural",
    "Guy (US, Male)": "en-US-GuyNeural",
    "Ryan (UK, Male)": "en-GB-RyanNeural",
    "Thomas (UK, Male)": "en-GB-ThomasNeural",
    "Prabhat (India, Male)": "en-IN-PrabhatNeural",
    "Neerja (India, Female)": "en-IN-NeerjaNeural",
}

# 📥 Read uploaded text file
def read_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        return uploaded_file.read().decode("utf-8")
    return ""

# 🧠 Save/load presets
PRESET_FILE = "tts_presets.json"

def save_presets(voice, rate, pitch):
    try:
        with open(PRESET_FILE, "w") as f:
            json.dump({"voice": voice, "rate": rate, "pitch": pitch}, f)
    except Exception as e:
        st.error(f"Error saving presets: {e}")

def load_presets():
    try:
        if os.path.exists(PRESET_FILE):
            with open(PRESET_FILE) as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Could not load presets: {e}")
    return {"voice": list(VOICES.keys())[0], "rate": 100, "pitch": 0}

# 🔊 Generate TTS audio
async def generate_tts(text, voice, filename, rate, pitch):
    ssml_text = f"""{text}"""
    communicate = edge_tts.Communicate(ssml_text, voice)
    communicate._ssml = True
    await communicate.save(filename)

# 🎼 Mix background music and voice with optional fade effects
def mix_with_music(voice_path, music_path, output_path, music_volume_pct, fade_in=False, fade_out=False):
    try:
        voice = AudioSegment.from_file(voice_path, format="mp3")
        music_format = music_path.split('.')[-1].lower()
        music = (
            AudioSegment.from_mp3(music_path)
            if music_format == 'mp3'
            else AudioSegment.from_wav(music_path)
            if music_format in ['wav', 'wave']
            else AudioSegment.from_file(music_path)
        )

        if len(voice) == 0 or len(music) == 0:
            st.error("❌ One of the audio files is empty or corrupted")
            return False

        if music_volume_pct == 0:
            mixed = voice
        else:
            if voice.frame_rate != music.frame_rate:
                music = music.set_frame_rate(voice.frame_rate)
            if voice.channels != music.channels:
                music = music.set_channels(voice.channels)

            volume_db = -30 + (music_volume_pct * 0.35)
            music = music + volume_db

            if len(music) < len(voice):
                music *= (len(voice) // len(music)) + 1
            music = music[:len(voice)]

            # Apply fade effects
            if fade_in:
                music = music.fade_in(3000)
            if fade_out:
                music = music.fade_out(3000)

            mixed = voice.overlay(music)

        mixed.export(output_path, format="mp3", bitrate="192k", parameters=["-q:a", "2"])
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

    except Exception as e:
        st.error(f"❌ Error mixing audio: {e}")
        return False

# 🧪 Test audio files
def test_audio_files(voice_path, music_path):
    try:
        voice = AudioSegment.from_file(voice_path)
        music = AudioSegment.from_file(music_path)
        test_music = music + (-20)
        test_music = test_music[:min(len(voice), 5000)]
        test_voice = voice[:min(len(voice), 5000)]
        test_mixed = test_voice.overlay(test_music)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as test_file:
            test_mixed.export(test_file.name, format="mp3")
            st.audio(test_file.name, format="audio/mp3")

        return True
    except Exception as e:
        st.error(f"❌ Audio test failed: {e}")
        return False

# 🏁 UI Layout
st.set_page_config(page_title="🗣️ Natural TTS", layout="centered")
st.title("🎧 AI Text-to-Speech with Music Mixer")

# 📝 Filename input
user_filename = st.text_input("📝 Enter a name for your audio file (no extension):", value="MyNarration")

# Sidebar: Upload text
st.sidebar.title("📄 Upload Text")
uploaded_txt = st.sidebar.file_uploader("Upload .txt file", type=["txt"])
uploaded_text = read_uploaded_file(uploaded_txt)

# Sidebar: Music upload
st.sidebar.title("🎼 Background Music")
use_music = st.sidebar.checkbox("Add background music")
uploaded_music = None
music_volume_pct = 30
fade_in_enabled = False
fade_out_enabled = False
if use_music:
    uploaded_music = st.sidebar.file_uploader("Upload music file (.mp3 or .wav)", type=["mp3", "wav"])
    music_volume_pct = st.sidebar.slider("Music Volume (%)", 0, 100, 30, step=5)
    fade_in_enabled = st.sidebar.checkbox("🎚️ Fade-in music", value=True)
    fade_out_enabled = st.sidebar.checkbox("🎚️ Fade-out music", value=True)

# Text input
default_text = uploaded_text if uploaded_text else ""
text = st.text_area("Enter text to convert:", value=default_text, height=200)

# Voice settings
st.subheader("🎙️ Voice Settings")
presets = load_presets()
voice_label = st.selectbox("Voice:", list(VOICES.keys()), index=list(VOICES.keys()).index(presets["voice"]))
rate = st.slider("Speed (%)", 50, 150, presets["rate"], step=5)
pitch = st.slider("Pitch (%)", -20, 20, presets["pitch"], step=1)

if st.button("💾 Save Preset"):
    save_presets(voice_label, rate, pitch)
    st.success("Preset saved!")

voice_id = VOICES[voice_label]

# Columns: Preview and Download
col1, col2 = st.columns(2)

# 🔊 Preview with mixing
with col1:
    if st.button("🔊 Preview"):
        if not text.strip():
            st.warning("Please enter some text!")
        else:
            with st.spinner("Generating preview..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_voice:
                        asyncio.run(generate_tts(text, voice_id, tmp_voice.name, rate, pitch))
                        final_preview_path = tmp_voice.name

                        if use_music and uploaded_music and music_volume_pct > 0:
                            music_ext = uploaded_music.name.split('.')[-1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{music_ext}") as tmp_music:
                                tmp_music.write(uploaded_music.getvalue())
                                music_path = tmp_music.name

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mixed:
                                preview_output = tmp_mixed.name

                            success = mix_with_music(
                                tmp_voice.name,
                                music_path,
                                preview_output,
                                music_volume_pct,
                                fade_in=fade_in_enabled,
                                fade_out=fade_out_enabled,
                            )

                            if success:
                                final_preview_path = preview_output
                                st.success("✅ Preview with music ready")

                        st.audio(final_preview_path, format="audio/mp3")
                except Exception as e:
                    st.error(f"Error generating preview: {e}")

# 📥 Download with optional testing
with col2:
    if st.button("📥 Download MP3"):
        if not text.strip():
            st.warning("Please enter some text!")
        else:
            with st.spinner("Rendering final audio..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_voice:
                        asyncio.run(generate_tts(text, voice_id, tmp_voice.name, rate, pitch))
                        final_output = tmp_voice.name

                        if use_music and uploaded_music and music_volume_pct > 0:
                            st.info("🎵 Mixing with background music...")

                            music_ext = uploaded_music.name.split('.')[-1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{music_ext}") as tmp_music:
                                tmp_music.write(uploaded_music.getvalue())
                                music_path = tmp_music.name

                            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mixed:
                                mixed_output = tmp_mixed.name

                            if st.checkbox("🧪 Test audio files first"):
                                test_audio_files(tmp_voice.name, music_path)

                            success = mix_with_music(
                                tmp_voice.name,
                                music_path,
                                mixed_output,
                                music_volume_pct,
                                fade_in=fade_in_enabled,
                                fade_out=fade_out_enabled,
                            )

                            if success:
                                final_output = mixed_output
                                st.success("✅ Audio mixed and ready")

                        # Generate filename from user input
                        filename = f"{user_filename.strip() or 'output'}.mp3"
                        with open(final_output, "rb") as f:
                            st.download_button(
                                label="📥 Download Final Audio",
                                data=f.read(),
                                file_name=filename,
                                mime="audio/mpeg"
                            )
                except Exception as e:
                    st.error(f"Error generating audio: {e}")

# 🛠️ Optional debug info
if st.checkbox("🔧 Show Debug Info"):
    st.write("**Settings:**")
    st.write(f"- Voice: {voice_label}")
    st.write(f"- Rate: {rate}%")
    st.write(f"- Pitch: {pitch}%")
    st.write(f"- Use Music: {use_music}")
    if use_music and uploaded_music:
        st.write(f"- Music File: {uploaded_music.name}")
        st.write(f"- Music Volume: {music_volume_pct}%")
        st.write(f"- Fade In: {fade_in_enabled}")
        st.write(f"- Fade Out: {fade_out_enabled}")
    st.write(f"- Output Filename: {user_filename.strip() or 'output'}.mp3")

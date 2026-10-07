import os
import sys
import asyncio
from typing import Optional
import edge_tts

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class VoiceService:
    def __init__(self, default_voice: str = "en-US-ChristopherNeural"):
        """
        Voices available:
        - en-US-ChristopherNeural (Rich audiobook narrator)
        - en-US-JennyNeural (Clear, natural female voice)
        - en-GB-RyanNeural (Classic British tone)
        """
        self.voice = default_voice

    async def text_to_speech_file(self, text: str, output_path: str = "response.mp3") -> str:
        """
        Converts text into high-quality neural voice audio and saves as an MP3 file.
        """
        # Clean markdown symbols like asterisks or brackets for cleaner speech
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")
        
        communicate = edge_tts.Communicate(clean_text, self.voice)
        await communicate.save(output_path)
        return output_path

    async def text_to_speech_bytes(self, text: str) -> bytes:
        """
        Returns raw MP3 audio bytes for streaming over web/API.
        """
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")
        communicate = edge_tts.Communicate(clean_text, self.voice)
        
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        return bytes(audio_data)

    def speak(self, text: str, output_path: str = "response.mp3") -> str:
        """
        Synchronous helper to generate audio easily.
        """
        return asyncio.run(self.text_to_speech_file(text, output_path))


if __name__ == "__main__":
    tts = VoiceService()
    test_phrase = (
        "Greetings! I am your AI book companion. "
        "According to Foundation History, Hari Seldon predicted the future using psychohistory."
    )
    print(f"🎙️ Generating voice for:\n\"{test_phrase}\"")
    output_file = tts.speak(test_phrase, "test_narration.mp3")
    print(f"✅ Audio generated successfully and saved to: {output_file}")
    
    # Try playing it automatically on Windows
    try:
        os.system(f"start {output_file}")
        print("🔊 Playing audio via default media player...")
    except Exception as e:
        print(f"Open {output_file} to listen.")

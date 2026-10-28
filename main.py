import os
import time
import requests
import asyncio
from google.generativeai import configure, GenerativeModel
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip

# ================= CONFIGURATION & SECRETS =================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")

# Initialize Gemini
configure(api_key=GEMINI_API_KEY)
model = GenerativeModel("gemini-1.5-flash")

# ================= STEP 1: GENERATE SCRIPT & CAPTION =================
def generate_content():
    prompt = (
        "Generate a short, engaging 3D cartoon story script in Maithili language for children (under 30 seconds). "
        "Also generate an SEO-optimized Facebook caption with hashtags in Maithili and English. "
        "Format the output strictly as: SCRIPT: [script text] || CAPTION: [caption text]"
    )
    response = model.generate_content(prompt)
    text = response.text
    
    parts = text.split("||")
    script_text = parts[0].replace("SCRIPT:", "").strip()
    caption_text = parts[1].replace("CAPTION:", "").strip()
    
    return script_text, caption_text

# ================= STEP 2: GENERATE VOICE OVER (Edge-TTS) =================
async def generate_audio(text, output_path="voice.mp3"):
    # Using Hindi/Nepali voice as closest approximation for Maithili support in Edge-TTS
    voice = "hi-IN-SwaraNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# ================= STEP 3: GENERATE 3D CARTOON IMAGE =================
def generate_image(output_path="image.jpg"):
    image_prompt = "Cute 3D Pixar style cartoon animals like a monkey and rabbit in a green forest, bright vibrant colors, 8k"
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(image_prompt)}"
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception("Failed to generate image from Pollinations.ai")

# ================= STEP 4: CREATE VIDEO WITH WATERMARK =================
def create_video(image_path="image.jpg", audio_path="voice.mp3", output_path="output_reel.mp4"):
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    
    image_clip = ImageClip(image_path).set_duration(duration)
    video_clip = image_clip.set_audio(audio_clip)
    
    # NOTE: MoviePy text overlay for custom watermark can be added here if needed,
    # keeping it lightweight and clean for cloud execution.
    video_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

# ================= STEP 5: FACEBOOK PUBLISHING API =================
def upload_facebook_reel(video_path, caption):
    init_url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/video_reels"
    payload = {
        "upload_phase": "start",
        "access_token": FB_PAGE_ACCESS_TOKEN
    }
    res = requests.post(init_url, data=payload).json()
    video_id = res.get("video_id")
    upload_url = res.get("upload_url")
    
    # Upload video binary
    with open(video_path, "rb") as f:
        headers = {"Authorization": f"OAuth {FB_PAGE_ACCESS_TOKEN}"}
        requests.post(upload_url, headers=headers, data=f)
    
    # Publish reel
    publish_url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/video_reels"
    publish_payload = {
        "video_id": video_id,
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "description": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN
    }
    pub_res = requests.post(publish_url, data=publish_payload).json()
    print("Reel Published Response:", pub_res)

def upload_facebook_photo(image_path, caption):
    url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
    with open(image_path, "rb") as f:
        files = {"source": f}
        payload = {
            "message": caption,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        res = requests.post(url, data=payload, files=files).json()
        print("Photo Post Published Response:", res)

# ================= MAIN PIPELINE =================
if __name__ == "__main__":
    print("1. Generating Script and Caption via Gemini...")
    script, caption = generate_content()
    
    print("2. Generating Voiceover...")
    asyncio.run(generate_audio(script))
    
    print("3. Generating 3D Cartoon Image...")
    generate_image()
    
    print("4. Creating Video with MoviePy...")
    create_video()
    
    print("5. Publishing Reel to Facebook Page...")
    upload_facebook_reel("output_reel.mp4", caption)
    
    print("Waiting for 5 minutes (300 seconds) before posting SEO Photo...")
    time.sleep(300)
    
    print("6. Publishing SEO Photo Post to Facebook Page...")
    upload_facebook_photo("image.jpg", caption + "\n\n#MaithiliShorts #3DCartoon #MaithiliKids")
    print("Automation Completed Successfully!")

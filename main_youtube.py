import os
import asyncio
from google.generativeai import configure, GenerativeModel
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ================= CONFIGURATION & SECRETS =================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

# Initialize Gemini
configure(api_key=GEMINI_API_KEY)
model = GenerativeModel("gemini-1.5-flash")

# ================= STEP 1: GENERATE SCRIPT & FULL SEO TITLE/DESC =================
def generate_youtube_content():
    prompt = (
        "Generate a short, engaging 3D cartoon story script in Maithili language for children (under 30 seconds). "
        "Also generate an SEO-optimized, highly trending YouTube Shorts title and a detailed description with relevant hashtags in Maithili and English. "
        "Format the output strictly as: SCRIPT: [script text] || TITLE: [title text] || DESCRIPTION: [description text]"
    )
    response = model.generate_content(prompt)
    text = response.text
    
    parts = text.split("||")
    script_text = parts[0].replace("SCRIPT:", "").strip()
    title_text = parts[1].replace("TITLE:", "").strip()
    desc_text = parts[2].replace("DESCRIPTION:", "").strip()
    
    return script_text, title_text, desc_text

# ================= STEP 2: GENERATE VOICE OVER (Edge-TTS) =================
async def generate_audio(text, output_path="voice.mp3"):
    voice = "hi-IN-SwaraNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# ================= STEP 3: GENERATE 3D CARTOON IMAGE (NO WATERMARK) =================
def generate_image(output_path="image.jpg"):
    image_prompt = "Cute 3D Pixar style cartoon animals like a clever monkey and a rabbit in a green magical forest, vertical 9:16 ratio, bright vibrant colors, 8k, highly detailed"
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(image_prompt)}"
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
    else:
        raise Exception("Failed to generate image from Pollinations.ai")

# ================= STEP 4: CREATE VERTICAL VIDEO (9:16 Shorts) =================
def create_youtube_video(image_path="image.jpg", audio_path="voice.mp3", output_path="output_short.mp4"):
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    
    image_clip = ImageClip(image_path).set_duration(duration).resize(height=1920)
    video_clip = image_clip.set_audio(audio_clip)
    
    video_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

# ================= STEP 5: YOUTUBE UPLOAD API =================
def upload_to_youtube(video_path, title, description):
    credentials = Credentials(
        None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    
    youtube = build("youtube", "v3", credentials=credentials)
    
    body = {
        "snippet": {
            "title": title,
            "description": description + "\n\n#MaithiliShorts #3DCartoon #MaithiliKids #Shorts #TrendingMaithili",
            "tags": ["Maithili Shorts", "3D Cartoon", "Maithili Kids Stories", "Maithili Kahani"],
            "categoryId": "24"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": True
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
            
    print("YouTube Short Uploaded Successfully! ID:", response.get('id'))

# ================= MAIN PIPELINE =================
if __name__ == "__main__":
    print("1. Generating Script, Full SEO Title and Description via Gemini...")
    script, title, description = generate_youtube_content()
    
    print("2. Generating Voiceover...")
    asyncio.run(generate_audio(script))
    
    print("3. Generating 3D Cartoon Image...")
    generate_image()
    
    print("4. Creating Vertical Video for YouTube Shorts...")
    create_youtube_video()
    
    print("5. Uploading to YouTube...")
    upload_to_youtube("output_short.mp4", title, description)
    print("YouTube Automation Completed Successfully!")

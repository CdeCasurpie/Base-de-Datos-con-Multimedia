import os
import yt_dlp

def descargar_playlist_mp3(playlist_url, output_dir="descargas"):
    os.makedirs(output_dir, exist_ok=True)
    opciones = {
        'format': 'bestaudio/best',
        'quiet': False,
        'outtmpl': f'{output_dir}/%(playlist_index)03d - %(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'yes_playlist': True,
    }

    with yt_dlp.YoutubeDL(opciones) as ydl:
        try:
            ydl.download([playlist_url])
            print("✅ Playlist descargada")
        except Exception as e:
            print("❌ Error al descargar playlist:", e)

if __name__ == "__main__":
    url = input("Pega el link de la playlist: ").strip()
    if url:
        descargar_playlist_mp3(url)

import subprocess
import shutil
import urllib.parse
import threading
import time
from ytmusicapi import YTMusic

class YTMusicPlayer:
    _ytmusic = None

    @classmethod
    def get_api(cls):
        if cls._ytmusic is None:
            try:
                cls._ytmusic = YTMusic()
            except Exception:
                cls._ytmusic = None
        return cls._ytmusic

    @classmethod
    def _force_play(cls):
        """Aguarda a aba abrir e dispara o play via MPRIS."""
        time.sleep(3.0)
        if shutil.which("playerctl"):
            subprocess.run(["playerctl", "play"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @classmethod
    def play_song(cls, query: str) -> str:
        """Busca a música, corrige o termo e abre no navegador disparando a reprodução."""
        clean_query = query.strip()
        if not clean_query:
            return "Qual música você gostaria de ouvir?"

        video_id = None
        track_name = clean_query
        artist_name = ""

        yt = cls.get_api()
        if yt:
            try:
                results = yt.search(clean_query, filter="songs")
                if not results:
                    results = yt.search(clean_query)

                if results:
                    top = results[0]
                    video_id = top.get("videoId")
                    track_name = top.get("title", clean_query)
                    if "artists" in top and top["artists"]:
                        artist_name = top["artists"][0].get("name", "")
            except Exception as e:
                print(f"[Geraldo:YTMusic Error]: {e}")

        if video_id:
            url = f"https://music.youtube.com/watch?v={video_id}"
            msg_art = f" de {artist_name}" if artist_name else ""
            response_text = f"Tocando {track_name}{msg_art} no YouTube Music."
        else:
            encoded = urllib.parse.quote_plus(clean_query)
            url = f"https://music.youtube.com/search?q={encoded}"
            response_text = f"Buscando {clean_query} no YouTube Music."

        try:
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            threading.Thread(target=cls._force_play, daemon=True).start()
            return response_text
        except Exception as e:
            return f"Não foi possível abrir o navegador: {e}"

    @classmethod
    def stop(cls) -> str:
        if shutil.which("playerctl"):
            subprocess.run(["playerctl", "pause"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "Reprodução pausada."
        return "Nenhum controle de mídia disponível."

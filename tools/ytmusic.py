from ytmusicapi import YTMusic
import subprocess
import re

class YTMusicPlayer:
    _yt = None

    @classmethod
    def get_instance(cls):
        if cls._yt is None:
            cls._yt = YTMusic()
        return cls._yt

    @classmethod
    def stop(cls, *args, **kwargs) -> str:
        subprocess.run(["playerctl", "stop"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Mídia parada."

    @classmethod
    def play_song(cls, query: str, item_type: str = "auto", *args, **kwargs) -> str:
        yt = cls.get_instance()
        
        # Limpeza de fonética e ruídos comuns de transcrição do Whisper
        clean = query.strip()
        clean = re.sub(r'\bdiana winehouse\b', 'Amy Winehouse', clean, flags=re.IGNORECASE)
        clean = re.sub(r'^(tokyo album|talk to album|talk to|toque o álbum|toque o album|toque|tocar|ouvir|coloque)\s+', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'^(the\s+)', '', clean, flags=re.IGNORECASE).strip()

        # Detecta se o pedido visa um álbum
        is_album_intent = (
            item_type == "album" or 
            any(w in query.lower() for w in ["álbum", "album", "discografia", "live at the bbc", "completo"])
        )

        query_busca = re.sub(r'\b(álbum|album|completo)\b', '', clean, flags=re.IGNORECASE).strip()

        try:
            # 1. Se houver intenção de álbum, busca primeiro com filter="albums"
            if is_album_intent:
                albums = yt.search(query_busca, filter="albums", limit=4)
                if albums:
                    first_album = albums[0]
                    album_title = first_album.get("title", "")
                    artist_name = first_album.get("artists", [{}])[0].get("name", "")
                    browse_id = first_album.get("browseId")

                    # Obtém os detalhes completos do álbum para extrair o playlistId e a 1ª faixa
                    album_data = yt.get_album(browse_id)
                    playlist_id = album_data.get("audioPlaylistId")
                    tracks = album_data.get("tracks", [])

                    if playlist_id:
                        if tracks:
                            first_video_id = tracks[0].get("videoId")
                            target_url = f"https://music.youtube.com/watch?v={first_video_id}&list={playlist_id}"
                        else:
                            target_url = f"https://music.youtube.com/playlist?list={playlist_id}"
                    else:
                        target_url = f"https://music.youtube.com/browse/{browse_id}"

                    # Abre diretamente no YouTube Music no navegador / PWA
                    subprocess.Popen(["xdg-open", target_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Abrindo o álbum {album_title} de {artist_name} no YouTube Music."

            # 2. Busca padrão por músicas/faixas individuais
            results = yt.search(query_busca, filter="songs", limit=4)
            if not results:
                results = yt.search(query_busca, limit=4)

            if not results:
                return f"Não encontrei resultados para {clean} no YouTube Music."

            first_track = results[0]
            video_id = first_track.get("videoId")
            title = first_track.get("title", clean)
            artist = first_track.get("artists", [{}])[0].get("name", "")

            target_url = f"https://music.youtube.com/watch?v={video_id}"
            subprocess.Popen(["xdg-open", target_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if artist:
                return f"Tocando {title} de {artist} no YouTube Music."
            return f"Tocando {title} no YouTube Music."

        except Exception as e:
            print(f"[Geraldo:YTMusic Error]: {e}")
            return "Ocorreu uma falha ao consultar o YouTube Music."

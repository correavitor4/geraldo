import pytest
import subprocess
from unittest.mock import patch, MagicMock
from tools.ytmusic import YTMusicPlayer

class TestYTMusicPlayer:
    def test_get_instance_singleton(self):
        with patch("tools.ytmusic.YTMusic") as mock_cls:
            instance1 = YTMusicPlayer.get_instance()
            instance2 = YTMusicPlayer.get_instance()
            assert instance1 is instance2

    def test_stop(self):
        res = YTMusicPlayer.stop()
        assert res == "Mídia parada."

    @patch.object(YTMusicPlayer, "_open_url")
    def test_play_song_standard(self, mock_open):
        mock_yt = MagicMock()
        mock_yt.search.return_value = [
            {"videoId": "abc123xyz", "title": "Bohemian Rhapsody", "artists": [{"name": "Queen"}]}
        ]
        with patch.object(YTMusicPlayer, "get_instance", return_value=mock_yt):
            res = YTMusicPlayer.play_song("toque Bohemian Rhapsody do Queen")
            assert "Tocando Bohemian Rhapsody de Queen" in res
            mock_open.assert_called_once_with("https://music.youtube.com/watch?v=abc123xyz")

    @patch.object(YTMusicPlayer, "_open_url")
    def test_play_song_whisper_diana_winehouse_cleanup(self, mock_open):
        mock_yt = MagicMock()
        mock_yt.search.return_value = [
            {"videoId": "wine123", "title": "Back to Black", "artists": [{"name": "Amy Winehouse"}]}
        ]
        with patch.object(YTMusicPlayer, "get_instance", return_value=mock_yt):
            res = YTMusicPlayer.play_song("coloque diana winehouse")
            assert "Amy Winehouse" in res
            # Verifica que a busca buscou por Amy Winehouse
            search_query = mock_yt.search.call_args[0][0]
            assert "Amy Winehouse" in search_query
            mock_open.assert_called_once_with("https://music.youtube.com/watch?v=wine123")

    @patch.object(YTMusicPlayer, "_open_url")
    def test_play_album(self, mock_open):
        mock_yt = MagicMock()
        mock_yt.search.return_value = [
            {"browseId": "MPREb_album_id", "title": "Back to Black", "artists": [{"name": "Amy Winehouse"}]}
        ]
        mock_yt.get_album.return_value = {
            "audioPlaylistId": "OLAK5uy_list_id",
            "tracks": [{"videoId": "track_1"}]
        }
        with patch.object(YTMusicPlayer, "get_instance", return_value=mock_yt):
            res = YTMusicPlayer.play_song("toque o álbum Back to Black", item_type="album")
            assert "Abrindo o álbum Back to Black de Amy Winehouse" in res
            mock_open.assert_called_once_with("https://music.youtube.com/watch?v=track_1&list=OLAK5uy_list_id")

    @patch("webbrowser.open", return_value=True)
    def test_open_url_browser(self, mock_browser):
        res = YTMusicPlayer._open_url("https://music.youtube.com")
        assert res is True
        mock_browser.assert_called_once_with("https://music.youtube.com")

    def test_play_song_not_found(self):
        mock_yt = MagicMock()
        mock_yt.search.return_value = []
        with patch.object(YTMusicPlayer, "get_instance", return_value=mock_yt):
            res = YTMusicPlayer.play_song("música_totalmente_inexistente_xyz_999")
            assert "Não encontrei resultados" in res

    def test_play_song_exception(self):
        mock_yt = MagicMock()
        mock_yt.search.side_effect = Exception("YTMusic network timeout")
        with patch.object(YTMusicPlayer, "get_instance", return_value=mock_yt):
            res = YTMusicPlayer.play_song("qualquer coisa")
            assert "Ocorreu uma falha ao consultar o YouTube Music" in res

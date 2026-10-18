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

    @patch("subprocess.run")
    def test_stop(self, mock_run):
        res = YTMusicPlayer.stop()
        assert res == "Mídia parada."
        mock_run.assert_called_once_with(
            ["playerctl", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    @patch("subprocess.Popen")
    def test_play_song_standard(self, mock_popen):
        mock_yt = MagicMock()
        mock_yt.search.return_value = [
            {"videoId": "abc123xyz", "title": "Bohemian Rhapsody", "artists": [{"name": "Queen"}]}
        ]
        with patch.object(YTMusicPlayer, "get_instance", return_value=mock_yt):
            res = YTMusicPlayer.play_song("toque Bohemian Rhapsody do Queen")
            assert "Tocando Bohemian Rhapsody de Queen" in res
            mock_popen.assert_called_once_with(
                ["xdg-open", "https://music.youtube.com/watch?v=abc123xyz"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

    @patch("subprocess.Popen")
    def test_play_song_whisper_diana_winehouse_cleanup(self, mock_popen):
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

    @patch("subprocess.Popen")
    def test_play_album(self, mock_popen):
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
            mock_popen.assert_called_once_with(
                ["xdg-open", "https://music.youtube.com/watch?v=track_1&list=OLAK5uy_list_id"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

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

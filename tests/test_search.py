import pytest
from unittest.mock import patch, MagicMock
from tools.search import WebSearchTools

class TestWebSearchTools:
    def test_search_web_current_affairs_news(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = [
            {"title": "Resultado do jogo", "body": "O time venceu por 2 a 1."},
            {"title": "Classificação", "body": "A equipe lidera o campeonato."}
        ]
        with patch("tools.search.DDGS", return_value=MagicMock(__enter__=lambda s: mock_ddgs_instance, __exit__=lambda s, *a: None)):
            res = WebSearchTools.search_web("resultado da partida")
            assert "Resultado do jogo: O time venceu por 2 a 1." in res
            assert "Classificação: A equipe lidera" in res
            mock_ddgs_instance.news.assert_called_once()

    def test_search_web_general_text(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = [
            {"title": "Distância da Terra até a Lua", "body": "A distância média é de cerca de 384.400 km."}
        ]
        with patch("tools.search.DDGS", return_value=MagicMock(__enter__=lambda s: mock_ddgs_instance, __exit__=lambda s, *a: None)):
            res = WebSearchTools.search_web("qual a distância da terra até a lua")
            assert "384.400 km" in res
            mock_ddgs_instance.text.assert_called_once()

    def test_search_web_news_empty_fallback_to_text(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.news.return_value = []
        mock_ddgs_instance.text.return_value = [
            {"title": "Notícia em texto", "body": "Conteúdo encontrado na busca de texto."}
        ]
        with patch("tools.search.DDGS", return_value=MagicMock(__enter__=lambda s: mock_ddgs_instance, __exit__=lambda s, *a: None)):
            res = WebSearchTools.search_web("notícia urgente")
            assert "Conteúdo encontrado na busca de texto" in res
            mock_ddgs_instance.news.assert_called_once()
            mock_ddgs_instance.text.assert_called_once()

    def test_search_web_no_results(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.text.return_value = []
        with patch("tools.search.DDGS", return_value=MagicMock(__enter__=lambda s: mock_ddgs_instance, __exit__=lambda s, *a: None)):
            res = WebSearchTools.search_web("termo_estranho_sem_resultado_123")
            assert "Não encontrei dados suficientes" in res

    def test_search_web_exception(self):
        with patch("tools.search.DDGS", side_effect=Exception("DDGS connection timeout")):
            res = WebSearchTools.search_web("qualquer coisa")
            assert "instabilidade na consulta de busca" in res

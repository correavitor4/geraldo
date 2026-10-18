import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock
from tools.news import NewsTools

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>G1</title>
    <item>
      <title>Descoberta importante na ciência e tecnologia - G1</title>
      <description>&lt;p&gt;Cientistas encontram nova partícula hoje.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Curto</title>
      <description>Ignorado por ser muito curto</description>
    </item>
    <item>
      <title>Segunda notícia relevante do dia no país | Portal</title>
      <description>Mais detalhes sobre economia e finanças.</description>
    </item>
  </channel>
</rss>
"""

class TestNewsTools:
    @patch("urllib.request.urlopen")
    def test_fetch_single_feed_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        items = NewsTools._fetch_single_feed("G1", "https://fake.url/rss")
        assert len(items) == 2
        assert items[0]["title"] == "Descoberta importante na ciência e tecnologia"
        assert items[0]["description"] == "Cientistas encontram nova partícula hoje."
        assert items[1]["title"] == "Segunda notícia relevante do dia no país"

    @patch("urllib.request.urlopen", side_effect=Exception("Network Down"))
    def test_fetch_single_feed_error(self, mock_urlopen):
        items = NewsTools._fetch_single_feed("G1", "https://fake.url/rss")
        assert items == []

    @patch.object(NewsTools, "_fetch_single_feed")
    def test_get_news_general(self, mock_fetch):
        mock_fetch.return_value = [
            {"source": "G1", "title": "Notícia Um Sobre Política Nacional", "description": "Desc 1"},
            {"source": "CNN", "title": "Notícia Um Sobre Política Nacional (outra fonte)", "description": "Desc 1 copy"},
            {"source": "G1", "title": "Notícia Dois Sobre Meio Ambiente", "description": "Desc 2"},
        ]
        res = NewsTools.get_news("geral")
        assert "Notícias compiladas" in res
        assert "Notícia Um Sobre Política Nacional" in res
        assert "Notícia Dois Sobre Meio Ambiente" in res

    @patch.object(NewsTools, "_fetch_single_feed", return_value=[])
    def test_get_news_general_empty(self, mock_fetch):
        res = NewsTools.get_news("geral")
        assert "Não foi possível carregar as notícias" in res

    @patch.object(NewsTools, "_fetch_single_feed")
    def test_get_news_topic_found(self, mock_fetch):
        mock_fetch.return_value = [
            {"source": "Google Notícias", "title": "Avanço histórico da IA", "description": "Novo modelo superinteligente."}
        ]
        res = NewsTools.get_news("inteligência artificial")
        assert "Avanço histórico da IA" in res
        assert "Novo modelo superinteligente" in res

    @patch.object(NewsTools, "_fetch_single_feed", return_value=[])
    def test_get_news_topic_empty(self, mock_fetch):
        res = NewsTools.get_news("assunto_inexistente_12345")
        assert "Não encontrei reportagens recentes sobre assunto_inexistente_12345" in res

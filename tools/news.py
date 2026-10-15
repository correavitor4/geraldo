import feedparser
import urllib.parse

class NewsTools:
    SECTIONS = {
        "geral": "https://g1.globo.com/rss/g1/",
        "tecnologia": "https://g1.globo.com/rss/g1/tecnologia/",
        "economia": "https://g1.globo.com/rss/g1/economia/",
        "mundo": "https://g1.globo.com/rss/g1/mundo/",
        "brasil": "https://feeds.bbci.co.uk/portuguese/rss.xml"
    }

    @classmethod
    def get_news(cls, query: str = "geral", limit: int = 4) -> str:
        """
        Consulta notícias. Se query for uma categoria padrão, busca no feed daquela seção.
        Se for um tema específico (ex: 'pesquisa eleitoral'), busca no Google Notícias.
        """
        clean = query.strip().lower()

        if clean in cls.SECTIONS:
            feed_url = cls.SECTIONS[clean]
            contexto = f"principais notícias de {clean}"
        else:
            # Busca temática direcionada no Google Notícias em português
            encoded_query = urllib.parse.quote_plus(clean)
            feed_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            contexto = f"notícias sobre {clean}"

        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                return f"Não encontrei notícias recentes sobre {clean}."

            headlines = []
            for i, entry in enumerate(feed.entries[:limit], start=1):
                title = entry.title.strip()
                # Limpa sufixos de fonte comum (ex: ' - G1', ' - BBC News Brasil')
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]
                headlines.append(f"{i}: {title}.")

            return f"Manchetes encontradas sobre {clean}: " + " ".join(headlines)

        except Exception as e:
            return f"Não foi possível carregar as notícias: {e}"

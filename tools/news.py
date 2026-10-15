import urllib.request
import xml.etree.ElementTree as ET
import html
import re
from concurrent.futures import ThreadPoolExecutor

class NewsTools:
    FEEDS = {
        "G1 Brasil": "https://g1.globo.com/rss/g1/",
        "G1 Goiás": "https://g1.globo.com/rss/g1/goias/",
        "CNN Brasil": "https://www.cnnbrasil.com.br/feed/",
        "Google Notícias": "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419"
    }

    @staticmethod
    def _fetch_single_feed(source_name: str, url: str) -> list:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) GeraldoVoice/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            items = []
            for item in root.findall("./channel/item")[:4]:
                title = item.findtext("title", "")
                title = html.unescape(title)
                # Limpa sufixos de jornais
                title = re.sub(r"\s*[-|]\s*[^-\|]+$", "", title).strip()
                
                desc = item.findtext("description", "")
                desc = html.unescape(re.sub(r"<[^>]+>", "", desc)).strip()

                if title and len(title) > 15:
                    items.append({
                        "source": source_name,
                        "title": title,
                        "description": desc[:140] if desc else ""
                    })
            return items
        except Exception as e:
            print(f"[Geraldo:News] Falha ao carregar feed '{source_name}': {e}")
            return []

    @classmethod
    def get_news(cls, query: str = "geral", *args, **kwargs) -> str:
        """Busca notícias em múltiplos portais jornalísticos em paralelo."""
        query_norm = query.lower().strip()
        
        # Se for busca por assunto específico, consulta via RSS de busca
        if query_norm not in ["geral", "notícias", "noticias", "dia", "últimas"]:
            encoded = urllib.parse.quote(query_norm)
            search_url = f"https://news.google.com/rss/search?q={encoded}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            results = cls._fetch_single_feed("Google Notícias", search_url)
            if not results:
                return f"Não encontrei reportagens recentes sobre {query}."
            noticias = [f"{n['title']}. {n['description']}" for n in results[:3]]
            return " ".join(noticias)

        # Se for notícias gerais do dia, consulta os portais em paralelo
        compiled_news = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(cls._fetch_single_feed, name, url)
                for name, url in cls.FEEDS.items()
            ]
            for f in futures:
                compiled_news.extend(f.result())

        if not compiled_news:
            return "Não foi possível carregar as notícias dos portais jornalísticos no momento."

        # Desduplicação simples por início do título
        unique_titles = {}
        for n in compiled_news:
            key = n["title"][:25].lower()
            if key not in unique_titles:
                unique_titles[key] = f"({n['source']}) {n['title']}"

        top_news = list(unique_titles.values())[:5]
        return "Notícias compiladas dos principais jornais: " + "; ".join(top_news)

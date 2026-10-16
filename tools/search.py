from ddgs import DDGS

class WebSearchTools:
    @staticmethod
    def search_web(query: str, max_results: int = 2, *args, **kwargs) -> str:
        """Executa buscas factuais e recentes via DDGS."""
        clean_query = query.strip()
        snippets = []

        try:
            with DDGS() as ddgs:
                # 1. Tenta notícias recentes se a consulta tiver perfil de atualidade
                termos_atualidades = ["pesquisa", "eleitoral", "eleição", "governo", "presidente", "jogo", "placar", "notícia", "resultado"]
                if any(t in clean_query.lower() for t in termos_atualidades):
                    try:
                        news_results = list(ddgs.news(
                            clean_query,
                            region="br-pt",
                            safesearch="moderate",
                            max_results=max_results
                        ))
                        for n in news_results:
                            title = n.get("title", "").strip()
                            body = n.get("body", "").strip()
                            if title and body:
                                snippets.append(f"{title}: {body}")
                    except Exception:
                        pass

                # 2. Se não pegou via news ou se não for tema de atualidade, busca texto geral
                if not snippets:
                    results = list(ddgs.text(
                        clean_query,
                        region="br-pt",
                        safesearch="moderate",
                        max_results=max_results
                    ))
                    for r in results:
                        title = r.get("title", "").strip()
                        body = r.get("body", "").strip()
                        if body:
                            snippets.append(f"{title}: {body}")

            if snippets:
                return " -- ".join(snippets[:3])

            return "Não encontrei dados suficientes na pesquisa online para esse assunto."

        except Exception as e:
            print(f"[Geraldo:Search Error]: {e}")
            return "Ocorreu uma instabilidade na consulta de busca."

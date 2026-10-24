"""
Testes massivos de compatibilidade cross-platform (Windows & Linux),
persistência integral de transcrição (.txt), geração de atas curtas vs longas (multi-página),
exportação customizada e seleção interativa no TUI.
"""
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import config
from services.meeting.models import MeetingSegment, MeetingSession, MeetingStatus, MeetingSummary
from services.meeting.manager import MeetingManager, sanitize_filename
from services.meeting.analyzer import (
    LocalMeetingAnalyzer,
    parse_summary_json,
    MEETING_CONCISE_SYSTEM_PROMPT,
    MEETING_DETAILED_SYSTEM_PROMPT,
)
from tools.meeting import MeetingTools
from core.ipc import GeraldoIPCServer


class TestWindowsCompatibility(unittest.TestCase):
    """Testes massivos de conformidade com regras de caminhos e nomes do Windows."""

    def test_sanitize_filename_windows_forbidden_chars(self):
        """Verifica que nenhum dos caracteres proibidos no Windows sobrevive ao sanitizador."""
        forbidden_inputs = [
            'Reunião <Diretoria> & "Conselho"',
            'Projeto: Fase 1 / Versão 2.0 \\ Alfa',
            'Relatório | Urgente ? Confidencial *',
            'Teste\x00com\x1fcontrole\t',
            'Arquivo com acentuação e cedilha: Ação e Coração',
            '   .nome_com_pontos_no_inicio_e_fim...   ',
        ]
        forbidden_regex = r'[<>:"/\\|?*\x00-\x1f]'

        for raw in forbidden_inputs:
            slug = sanitize_filename(raw)
            self.assertFalse(any(c in slug for c in '<>:"/\\|?*'), f"Falhou para: {raw} -> {slug}")
            self.assertFalse(slug.startswith("."), f"Não pode começar com ponto no Windows: {slug}")
            self.assertFalse(slug.endswith("."), f"Não pode terminar com ponto no Windows: {slug}")
            self.assertFalse(slug.endswith(" "), f"Não pode terminar com espaço no Windows: {slug}")
            self.assertTrue(len(slug) <= 50, "Deve respeitar limite seguro de tamanho")

    def test_sanitize_filename_windows_reserved_names(self):
        """Verifica proteção contra nomes de dispositivos reservados no Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9)."""
        reserved = ["CON", "prn", "AUX", "nul", "COM1", "com9", "LPT1", "lpt9"]
        for res_name in reserved:
            slug = sanitize_filename(res_name)
            self.assertNotEqual(slug.lower(), res_name.lower(), f"Nome reservado não foi protegido: {res_name} -> {slug}")
            self.assertTrue(slug.startswith("reuniao"), f"Deve prefixar nome reservado: {slug}")

    def test_windows_paths_normalization(self):
        """Garante que separadores e caminhos são normalizados de forma segura."""
        with tempfile.TemporaryDirectory() as tmp_root:
            # Simula subpastas usando separador do SO e caminhos com redundâncias
            raw_path = os.path.join(tmp_root, "pasta1", "..", "pasta1", "reunioes")
            norm = os.path.normpath(raw_path)
            self.assertNotIn("..", norm)

            mgr = MeetingManager(storage_dir=norm)
            self.assertEqual(mgr.storage_dir, os.path.normpath(os.path.abspath(norm)))
            self.assertTrue(os.path.exists(mgr.transcricoes_dir))
            self.assertTrue(os.path.exists(mgr.atas_dir))
            self.assertTrue(os.path.exists(mgr.recordings_dir))
            self.assertTrue(os.path.exists(mgr.export_dir))


class TestTranscriptPersistenceAndExport(unittest.TestCase):
    """Testes da persistência completa da transcrição em arquivo e exportação."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.export_dir = os.path.join(self.tmp_dir, "minhas_exportadas")
        self.manager = MeetingManager(
            storage_dir=self.tmp_dir,
            default_provider="local",
            default_detail_level="detailed",
            transcriber=MagicMock(),
            analyzer=MagicMock(),
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_full_raw_transcript_saved_to_dedicated_file(self):
        """Verifica se o texto integral da reunião é salvo em .txt com timestamps e metadados."""
        sample_segments = [
            MeetingSegment(start=0.0, end=4.5, text="Bom dia a todos, iniciamos nosso alinhamento sobre o produto.", speaker="Vitor"),
            MeetingSegment(start=4.5, end=10.2, text="Perfeito. A arquitetura de sincronização está pronta.", speaker="Geraldo"),
            MeetingSegment(start=10.2, end=18.0, text="Excelente. O prazo final ficou acordado para sexta-feira.", speaker="Vitor"),
        ]
        self.manager._custom_transcriber.transcribe.return_value = sample_segments
        self.manager._custom_analyzer.analyze.return_value = MeetingSummary(
            title="Alinhamento de Produto",
            date="24/10/2026 10:00",
            duration_seconds=18.0,
            executive_summary="Alinhamento da arquitetura do produto.",
            topics=["Arquitetura de Sincronização"],
            decisions=["Entrega confirmada para sexta-feira."],
            action_items=[{"task": "Finalizar sincronização", "owner": "Geraldo", "deadline": "Sexta", "priority": "Alta"}],
            detail_level="detailed",
        )

        # Inicia e para sessão
        session = self.manager.start_meeting(title="Alinhamento de Produto", detail_level="detailed")
        self.manager.stop_meeting()

        # Processa
        processed = self.manager.process_meeting_sync(session.session_id)

        # Validações da persistência
        self.assertIsNotNone(processed.transcript_path)
        self.assertTrue(os.path.exists(processed.transcript_path))
        self.assertTrue(processed.transcript_path.endswith(".txt"))
        self.assertTrue(os.path.exists(processed.output_markdown_path))
        self.assertTrue(processed.output_markdown_path.endswith(".md"))

        # Lê conteúdo da transcrição bruta
        with open(processed.transcript_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("TRANSCRIÇÃO INTEGRAL DE REUNIÃO", content)
        self.assertIn("Alinhamento de Produto", content)
        self.assertIn("[Vitor] Bom dia a todos", content)
        self.assertIn("[Geraldo] Perfeito. A arquitetura", content)
        self.assertIn("[00:00 - 00:04]", content)

    def test_export_meeting_to_custom_directory_and_files(self):
        """Testa exportação para pasta customizada escolhida pelo usuário."""
        mock_rec = MagicMock()
        mock_rec.stop.return_value = 10.0
        self.manager._current_recorder = mock_rec
        session = self.manager.start_meeting(title="Reunião com Diretoria")
        self.manager._current_recorder = mock_rec
        self.manager.stop_meeting()

        session.summary = MeetingSummary(
            title="Reunião com Diretoria",
            date="24/10/2026 14:00",
            duration_seconds=60.0,
            executive_summary="Discussão estratégica de metas.",
            topics=["Metas 2027"],
            decisions=["Aprovar orçamento."],
            action_items=[],
            detail_level="detailed",
        )
        session.transcript_segments = [MeetingSegment(start=0, end=10, text="Olá mundo", speaker="Diretor")]
        
        # Simula criação de arquivos originais
        dummy_md = os.path.join(self.manager.atas_dir, "teste.md")
        with open(dummy_md, "w", encoding="utf-8") as f:
            f.write("# Ata Original")
        session.output_markdown_path = dummy_md

        dummy_txt = os.path.join(self.manager.transcricoes_dir, "teste.txt")
        with open(dummy_txt, "w", encoding="utf-8") as f:
            f.write("Transcrição Original")
        session.transcript_path = dummy_txt

        # 1. Exporta para diretório customizado
        res = self.manager.export_meeting(session.session_id, target_dir_or_file=self.export_dir, format_type="both")
        self.assertIn("markdown_path", res)
        self.assertIn("transcript_path", res)
        self.assertTrue(os.path.exists(res["markdown_path"]))
        self.assertTrue(os.path.exists(res["transcript_path"]))

        # 2. Exporta para arquivo específico .md
        custom_md_file = os.path.join(self.tmp_dir, "custom_export_teste.md")
        res_file = self.manager.export_meeting(session.session_id, target_dir_or_file=custom_md_file)
        self.assertEqual(res_file.get("markdown_path"), os.path.normpath(custom_md_file))
        self.assertTrue(os.path.exists(custom_md_file))


class TestDetailLevelAndMultiPageGeneration(unittest.TestCase):
    """Testa geração de atas curtas (executivas) vs longas (multi-página com riqueza de detalhes)."""

    def test_concise_mode_generation(self):
        """Modo Curto: gera síntese executiva direta sem páginas excessivas."""
        summary = MeetingSummary(
            title="Alinhamento Curto",
            date="24/10/2026 09:00",
            duration_seconds=120.0,
            executive_summary="Alinhamento rápido de 5 minutos para destravar deploys.",
            topics=["Deploy de Emergência"],
            decisions=["Fazer rollback imediato"],
            action_items=[{"task": "Executar rollback", "owner": "DevOps", "deadline": "Imediato"}],
            detail_level="concise",
        )
        segs = [MeetingSegment(start=0, end=30, text="Vamos fazer rollback rápido.", speaker="Tech Lead")]
        md = summary.to_markdown(segs)

        self.assertIn("# 📋 Ata de Reunião: Alinhamento Curto", md)
        self.assertIn("Síntese Executiva Concisa", md)
        self.assertIn("Deploy de Emergência", md)
        self.assertIn("Fazer rollback imediato", md)
        # Não deve conter seções longas de governança quando concise
        self.assertNotIn("Discussão Minuciosa por Tópicos", md)
        self.assertNotIn("Riscos, Gargalos e Pontos de Atenção", md)

    def test_detailed_mode_multi_page_generation(self):
        """Modo Longo: gera ata exaustiva, de várias seções e páginas densas."""
        summary = MeetingSummary(
            title="Conselho de Administração - Planejamento Estratégico",
            date="24/10/2026 15:00",
            duration_seconds=3600.0,
            context="Sessão ordinária do conselho destinada à revisão orçamentária do ano fiscal de 2027 e expansão da infraestrutura local de inteligência artificial.",
            executive_summary="O conselho debateu a viabilidade de operar 100% on-premises em Anápolis, ponderando custos operacionais contra garantias de sigilo. A decisão unânime foi investir na aquisição de hardware local.",
            detailed_discussions=[
                {
                    "topic": "Migração para Hardware Local",
                    "details": "Foi apresentado estudo técnico de TCO demonstrando economia de 42% no horizonte de 3 anos frente à nuvem proprietária.",
                    "arguments": "Os diretores de TI enfatizaram a confidencialidade das conversas com clientes locais, enquanto a diretoria financeira alertou para o CAPEX inicial.",
                    "conclusions": "O conselho deliberou pelo avanço da aquisição mediante linha de crédito incentivada."
                },
                {
                    "topic": "Governança e Política de Privacidade de Áudio",
                    "details": "Definição do ciclo de vida das gravações WAV e anonimização de dados sensíveis nas transcrições salvas.",
                    "arguments": "Conformidade integral com LGPD sem envio de gravações para servidores fora do território nacional.",
                    "conclusions": "Aprovada a política de expurgo automático de áudios brutos após 90 dias com retenção perpétua das atas em Markdown."
                }
            ],
            topics=["Migração para Hardware Local", "Governança de Áudio"],
            decisions=[
                "Aprovar orçamento de R$ 250.000,00 para novos servidores locais de inferência com GPUs dedicadas.",
                "Homologar a política de segurança e expurgo de áudios conforme LGPD."
            ],
            risks_and_concerns=[
                "Volatilidade cambial no fornecimento de chips de aceleração gráfica.",
                "Necessidade de climatização e nobreak redundante no datacenter local."
            ],
            action_items=[
                {"task": "Emitir RFP de compras dos servidores", "owner": "Diretoria de Operações", "deadline": "15/11/2026", "priority": "Alta"},
                {"task": "Elaborar minuta contratual com fornecedores", "owner": "Jurídico", "deadline": "20/11/2026", "priority": "Média"},
            ],
            next_steps=[
                "Apresentação da proposta vencedora da RFP na sessão de 01/12/2026.",
                "Início do comissionamento das máquinas em Janeiro de 2027."
            ],
            detail_level="detailed",
        )
        segs = [
            MeetingSegment(start=0, end=15, text="Iniciamos a reunião com a ordem do dia.", speaker="Presidente"),
            MeetingSegment(start=15, end=45, text="Apresento aqui o TCO da migração on-premises.", speaker="Diretor TI"),
        ]

        md = summary.to_markdown(segs)

        # Verificações de estrutura multi-página
        self.assertIn("# 📋 Ata de Reunião: Conselho de Administração", md)
        self.assertIn("1. Contexto, Motivação e Objetivos da Sessão", md)
        self.assertIn("Resumo Executivo", md)
        self.assertIn("3. Discussão Minuciosa por Tópicos", md)
        self.assertIn("3.1. Migração para Hardware Local", md)
        self.assertIn("TCO demonstrando economia de 42%", md)
        self.assertIn("3.2. Governança e Política de Privacidade de Áudio", md)
        self.assertIn("4. Decisões Tomadas e Deliberações", md)
        self.assertIn("5. Riscos, Gargalos e Pontos de Atenção", md)
        self.assertIn("6. Tarefas e Próximos Passos (Action Items)", md)
        self.assertIn("7. Próximos Passos e Encaminhamentos", md)
        self.assertIn("Transcrição Bruta Completa", md)
        self.assertTrue(len(md) > 2000, "Ata detalhada deve ser longa e substancial (multi-página)")

    def test_analyzer_prompt_selection_and_num_predict(self):
        """Verifica se o analisador seleciona prompts distintos e num_predict adequado."""
        analyzer = LocalMeetingAnalyzer(host="http://localhost:11434", model="qwen2.5:3b")
        self.assertEqual(analyzer.num_ctx, 16384)

        # Mock de chamada HTTP
        with patch("urllib.request.urlopen") as mock_url:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"message": {"content": "```json\\n{\\"title\\": \\"Teste Longo\\", \\"executive_summary\\": \\"Resumo\\", \\"topics\\": [], \\"decisions\\": [], \\"action_items\\": []}\\n```"}}'
            mock_url.return_value.__enter__.return_value = mock_resp

            res_detailed = analyzer.analyze("Texto", metadata={"detail_level": "detailed"})
            self.assertEqual(res_detailed.detail_level, "detailed")

            # Verifica payload enviado
            req = mock_url.call_args[0][0]
            import json
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["options"]["num_predict"], 4096)
            self.assertIn("auditor e secretário executivo", payload["messages"][0]["content"])

            # Agora testa modo conciso
            res_concise = analyzer.analyze("Texto", metadata={"detail_level": "concise"})
            self.assertEqual(res_concise.detail_level, "concise")
            payload_concise = json.loads(mock_url.call_args[0][0].data.decode("utf-8"))
            self.assertEqual(payload_concise["options"]["num_predict"], 1024)
            self.assertIn("direta e concisa", payload_concise["messages"][0]["content"])


class TestConfigAndIPCHandlers(unittest.TestCase):
    """Testa novos campos de configuração e endpoints IPC RPC."""

    def test_config_update_and_get(self):
        """Testa get_meeting_config e update_meeting_config com detail_level e export_dir."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_cfg = config.get_meeting_config()
            try:
                cfg = config.update_meeting_config(
                    provider="cloud",
                    storage_dir=tmp_dir,
                    export_dir=os.path.join(tmp_dir, "export"),
                    detail_level="longo",
                    persist=False,
                )
                self.assertEqual(cfg["provider"], "cloud")
                self.assertEqual(cfg["detail_level"], "detailed")
                self.assertEqual(cfg["storage_dir"], os.path.normpath(tmp_dir))
                self.assertEqual(cfg["export_dir"], os.path.normpath(os.path.join(tmp_dir, "export")))

                # Teste modo curto
                cfg2 = config.update_meeting_config(detail_level="curto", persist=False)
                self.assertEqual(cfg2["detail_level"], "concise")
            finally:
                # Restaura
                config.update_meeting_config(
                    provider=orig_cfg["provider"],
                    storage_dir=orig_cfg["storage_dir"],
                    export_dir=orig_cfg.get("export_dir"),
                    detail_level=orig_cfg.get("detail_level"),
                    persist=False,
                )

    def test_ipc_meeting_export_and_start_with_detail(self):
        """Verifica handlers RPC do IPC para meeting_start com detail_level e meeting_export."""
        ipc = GeraldoIPCServer()

        with tempfile.TemporaryDirectory() as tmp_dir:
            mgr = MeetingManager(storage_dir=tmp_dir)
            MeetingTools.reset_for_tests(mgr)

            # Inicia com detail_level
            start_res = ipc._handle_meeting_start({"title": "Reunião IPC", "detail_level": "concise", "provider": "local"})
            self.assertIn("concisa", start_res["message"].lower())
            active = mgr.active_session
            self.assertEqual(active.detail_level, "concise")

            # Finaliza
            mgr.stop_meeting()

            # Cria ata fake
            active.summary = MeetingSummary(
                title="Reunião IPC",
                date="24/10/2026",
                duration_seconds=30.0,
                executive_summary="Resumo",
                detail_level="concise",
            )
            dummy_txt = os.path.join(mgr.transcricoes_dir, "transc.txt")
            with open(dummy_txt, "w", encoding="utf-8") as f:
                f.write("Texto")
            active.transcript_path = dummy_txt

            # Exporta via IPC
            exp_res = ipc._handle_meeting_export({"session_id": active.session_id})
            self.assertEqual(exp_res["session_id"], active.session_id)
            self.assertTrue(os.path.exists(exp_res["exported"]["transcript_path"]))


if __name__ == "__main__":
    unittest.main()

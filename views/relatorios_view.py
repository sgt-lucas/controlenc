import flet as ft
from datetime import datetime, date
import pandas as pd
import traceback 
import io        
import os        
import uuid      
import database # TÉCNICO: Motor PostgreSQL 17 local

# Importações do ReportLab permanecem as mesmas para manter o layout dos PDFs
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

class RelatoriosView(ft.Column):
    """
    Representa o conteúdo da aba Relatórios.
    (v1.3) Adiciona scroll vertical.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.error_modal = error_modal
        
        # --- (CORREÇÃO v1.3) ---
        # Adiciona o scroll de volta à coluna principal da view
        self.scroll = ft.ScrollMode.ADAPTIVE
        # --- (FIM DA CORREÇÃO v1.3) ---
        
        self.progress_ring = ft.ProgressRing(visible=False, width=32, height=32)

        # --- Controlos de Download (v8.0 - mantidos) ---
        self.tipo_ficheiro_a_salvar = None 
        self.dados_relatorio_para_salvar = None 
        
        self.download_button_geral = ft.ElevatedButton(
            text="Baixar Relatório", 
            icon="DOWNLOAD",
            visible=False, 
            on_click=lambda e: print("Botão de download geral clicado (URL ainda não definida)")
        )
        self.download_button_extrato = ft.ElevatedButton(
            text="Baixar Extrato", 
            icon="DOWNLOAD",
            visible=False,
            on_click=lambda e: print("Botão de download extrato clicado (URL ainda não definida)")
        )
        # --- Fim dos controlos de Download ---

        # --- Secção: Relatório Geral NCs (Controlos) ---
        self.filtro_data_inicio = ft.TextField(label="Data Início (Receb.)", hint_text="AAAA-MM-DD", width=150, tooltip="Data de recebimento inicial", read_only=True)
        self.filtro_data_fim = ft.TextField(label="Data Fim (Receb.)", hint_text="AAAA-MM-DD", width=150, tooltip="Data de recebimento final", read_only=True)
        self.btn_abrir_data_inicio = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Data Início", on_click=lambda e: self.open_datepicker(self.date_picker_inicio))
        self.btn_abrir_data_fim = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Data Fim", on_click=lambda e: self.open_datepicker(self.date_picker_fim))
        
        self.date_picker_inicio = ft.DatePicker(on_change=self.handle_start_date_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        self.date_picker_fim = ft.DatePicker(on_change=self.handle_end_date_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        
        self.filtro_pi = ft.Dropdown( label="Filtrar por PI", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.on_pi_filter_change )
        self.filtro_nd = ft.Dropdown( label="Filtrar por ND", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True )
        self.filtro_status = ft.Dropdown( label="Filtrar por Status", options=[ ft.dropdown.Option(text="Todos", key=None), ft.dropdown.Option(text="Ativa", key="Ativa"), ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"), ft.dropdown.Option(text="Vencida", key="Vencida"), ft.dropdown.Option(text="Cancelada", key="Cancelada"),], width=200 )
        self.btn_limpar_filtros_geral = ft.IconButton(icon="CLEAR_ALL", tooltip="Limpar Filtros (Rel. Geral)", on_click=self.limpar_filtros_geral)

        self.btn_gerar_excel_geral = ft.ElevatedButton("Gerar Excel Geral (.xlsx)", icon="TABLE_CHART", on_click=self.gerar_relatorio_geral_excel)
        self.btn_gerar_pdf_geral = ft.ElevatedButton("Gerar PDF Geral (.pdf)", icon="PICTURE_AS_PDF", on_click=self.gerar_relatorio_geral_pdf)

        # --- Secção: Relatório Individual (Extrato) (Controlos) ---
        self.dropdown_nc_extrato = ft.Dropdown(
            label="Selecione a NC para gerar o Extrato",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True
        )
        self.btn_gerar_excel_extrato = ft.ElevatedButton("Gerar Extrato Excel", icon="TABLE_CHART", on_click=self.gerar_extrato_excel)
        self.btn_gerar_pdf_extrato = ft.ElevatedButton("Gerar Extrato PDF", icon="PICTURE_AS_PDF", on_click=self.gerar_extrato_pdf)
        
        
        # --- (INÍCIO DA REFATORAÇÃO VISUAL v1.2) ---
        
        # Card 1: Relatório Geral
        card_relatorio_geral = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Relatório Geral de Notas de Crédito", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.IconButton(
                                        icon="REFRESH", 
                                        on_click=self.load_all_filters_wrapper, 
                                        tooltip="Recarregar Listas de Filtros"
                                    ),
                                    self.progress_ring,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Divider(),
                        ft.Text("Filtros (Relatório Geral):", weight=ft.FontWeight.BOLD),
                        ft.Row([ self.filtro_data_inicio, self.btn_abrir_data_inicio, ft.Container(width=20), self.filtro_data_fim, self.btn_abrir_data_fim, ], alignment=ft.MainAxisAlignment.START),
                        ft.Row([self.filtro_pi, self.filtro_nd]),
                        ft.Row([self.filtro_status, self.btn_limpar_filtros_geral], alignment=ft.MainAxisAlignment.START),
                        ft.Row([self.btn_gerar_excel_geral, self.btn_gerar_pdf_geral], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(self.download_button_geral, alignment=ft.alignment.center),
                    ],
                    spacing=15
                )
            )
        )
        
        # Card 2: Relatório Individual
        card_relatorio_extrato = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("Relatório Individual (Extrato) por NC", size=20, weight=ft.FontWeight.W_600),
                        ft.Divider(),
                        ft.Row([self.dropdown_nc_extrato]),
                        ft.Row([self.btn_gerar_excel_extrato, self.btn_gerar_pdf_extrato], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(self.download_button_extrato, alignment=ft.alignment.center),
                    ],
                    spacing=15
                )
            )
        )

        self.controls = [
            card_relatorio_geral,
            card_relatorio_extrato
        ]
        # --- (FIM DA REFATORAÇÃO VISUAL v1.2) ---

        if self.page:
            self.page.overlay.extend([
                self.date_picker_inicio, 
                self.date_picker_fim, 
            ])

        self.on_mount = self.on_view_mount
        
    # -----------------------------------------------------------------
    # O RESTANTE DO FICHEIRO (todas as funções de lógica v8.0)
    # permanece EXATAMENTE IGUAL.
    # -----------------------------------------------------------------
        
    def on_view_mount(self, e):
        print("RelatoriosView: Controlo montado. A carregar dados...")
        self.load_all_filters() 
        
    def show_error(self, message):
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Trata erros do motor PostgreSQL 17 local."""
        msg = str(ex).lower()
        print(f"Erro de Banco Local ({context}): {msg}") 
        if "connection" in msg or "refused" in msg:
            self.show_error("Erro de Conexão: O servidor PostgreSQL 17 local não responde.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {ex}")

    def show_success_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()
             
    def formatar_moeda(self, valor):
        try: val = float(valor); return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError): return "R$ 0,00"

    def open_datepicker(self, picker: ft.DatePicker):
        if picker and self.page: 
            if picker not in self.page.overlay:
                self.page.overlay.append(picker)
            picker.open = True # O comando correto é .open = True
            self.page.update()

    def handle_start_date_change(self, e):
        selected_date = e.control.value
        self.filtro_data_inicio.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        self.filtro_data_inicio.update() 
        if self.page: self.page.update() 

    def handle_end_date_change(self, e):
        selected_date = e.control.value
        self.filtro_data_fim.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        self.filtro_data_fim.update() 
        if self.page: self.page.update() 

    def load_all_filters_wrapper(self, e):
        print("Relatórios: Recarregando todos os filtros...")
        self.progress_ring.visible = True
        self.update() 
        try:
            self.load_all_filters()
            self.show_success_snackbar("Filtros atualizados com sucesso.")
        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO RELATORIOS [load_all_filters_wrapper] ---")
            traceback.print_exc()
            print("--------------------------------------------------------------------------")
            self.handle_db_error(ex, "recarregar filtros")
        finally: 
            self.progress_ring.visible = False
            self.update() 
        
    def load_all_filters(self):
        self.load_filter_options()
        self.load_nc_list_for_statement_filter()
    
    def load_filter_options(self, pi_selecionado=None):
        """Busca PIs e NDs únicos no banco local para os filtros de relatório."""
        try:
            if pi_selecionado is None:
                print("Relatórios: A carregar PIs e NDs do banco local...")
                # TÉCNICO: SELECT DISTINCT nativo do Postgres
                pis = database.execute_query("SELECT DISTINCT pi FROM ncs_com_saldos ORDER BY pi")
                self.filtro_pi.options = [ft.dropdown.Option(text="Todos os PIs", key=None)]
                if pis:
                    for row in pis:
                        if row['pi']: self.filtro_pi.options.append(ft.dropdown.Option(text=row['pi'], key=row['pi']))
                
                nds = database.execute_query("SELECT DISTINCT natureza_despesa FROM ncs_com_saldos ORDER BY natureza_despesa")
                self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key=None)]
                if nds:
                    for row in nds:
                        if row['natureza_despesa']: self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
            else:
                # Filtro dependente (NDs por PI)
                sql = "SELECT DISTINCT natureza_despesa FROM ncs_com_saldos WHERE pi = %s ORDER BY natureza_despesa"
                nds = database.execute_query(sql, (pi_selecionado,))
                self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key=None)]
                if nds:
                    for row in nds:
                        self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
            
            if self.page: self.update()
        except Exception as ex: 
            traceback.print_exc()
            self.handle_db_error(ex, "carregar filtros de PI/ND")

    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_filter_options(pi_selecionado=pi_val)

    def limpar_filtros_geral(self, e):
        print("Relatórios: A limpar filtros do Relatório Geral...");
        self.filtro_data_inicio.value = ""; self.filtro_data_fim.value = ""
        self.filtro_pi.value = None; self.filtro_nd.value = None
        self.filtro_status.value = None
        self.download_button_geral.visible = False
        self.load_filter_options(pi_selecionado=None)
        if self.page: self.page.update() 
        
    def fetch_report_data_geral(self, e): 
        """Busca dados no PostgreSQL 17 para o Relatório Geral."""
        print("Relatórios: A buscar dados filtrados localmente...")
        try:
            # TÉCNICO: Uso da view ncs_com_saldos para dados já calculados
            sql = "SELECT * FROM ncs_com_saldos WHERE 1=1"
            params = []

            if self.filtro_data_inicio.value:
                sql += " AND data_recebimento >= %s"; params.append(self.filtro_data_inicio.value)
            if self.filtro_data_fim.value:
                sql += " AND data_recebimento <= %s"; params.append(self.filtro_data_fim.value)
            if self.filtro_status.value:
                sql += " AND status_calculado = %s"; params.append(self.filtro_status.value)
            if self.filtro_pi.value:
                sql += " AND pi = %s"; params.append(self.filtro_pi.value)
            if self.filtro_nd.value:
                sql += " AND natureza_despesa = %s"; params.append(self.filtro_nd.value)

            sql += " ORDER BY data_recebimento DESC"
            dados = database.execute_query(sql, tuple(params))
            
            if dados: 
                print(f"Relatórios: {len(dados)} registros encontrados.") 
                return dados
            else: 
                self.page.snack_bar = ft.SnackBar(ft.Text("Nenhum registro encontrado com estes filtros."), bgcolor="orange")
                self.page.snack_bar.open = True
                self.page.update()
                return None
        except Exception as ex: 
            self.handle_db_error(ex, "buscar dados do Relatório Geral") 
            return None
            
    def fetch_report_data_extrato(self, nc_id):
        """Busca o histórico completo de uma NC, incluindo SEÇÕES e seus saldos."""
        if not nc_id: return None
        print(f"Relatórios: A gerar extrato completo para NC ID: {nc_id}...")
        try:
            # 1. Dados da NC
            nc_res = database.execute_query("SELECT * FROM notas_de_credito WHERE id = %s", (nc_id,))
            if not nc_res: return None
            
            # 2. Dados das Seções (Cotas) com Saldo Calculado
            # (Igual ao Quick View)
            sql_secoes = """
                SELECT s.nome, d.valor_alocado, 
                       COALESCE((SELECT SUM(valor_empenhado) FROM notas_de_empenho WHERE id_distribuicao = d.id), 0) as emp,
                       COALESCE((SELECT SUM(valor_recolhido) FROM recolhimentos_de_saldo WHERE id_distribuicao = d.id), 0) as rec
                FROM distribuicao_nc_secoes d
                JOIN secoes s ON s.id = d.id_secao
                WHERE d.id_nc = %s
                ORDER BY s.nome
            """
            secoes_res = database.execute_query(sql_secoes, (nc_id,))
            
            # 3. Notas de Empenho (Com nome da seção)
            sql_nes = """
                SELECT ne.*, s.nome as nome_secao 
                FROM notas_de_empenho ne
                JOIN distribuicao_nc_secoes d ON ne.id_distribuicao = d.id
                JOIN secoes s ON s.id = d.id_secao
                WHERE d.id_nc = %s 
                ORDER BY ne.data_empenho DESC
            """
            nes_res = database.execute_query(sql_nes, (nc_id,))
            
            # 4. Recolhimentos (Com nome da seção)
            sql_rec = """
                SELECT r.*, s.nome as nome_secao
                FROM recolhimentos_de_saldo r
                JOIN distribuicao_nc_secoes d ON r.id_distribuicao = d.id
                JOIN secoes s ON s.id = d.id_secao
                WHERE r.id_nc = %s 
                ORDER BY r.data_recolhimento DESC
            """
            rec_res = database.execute_query(sql_rec, (nc_id,))
            
            return { 
                "nc": nc_res[0], 
                "secoes": secoes_res if secoes_res else [], # Novo Campo
                "nes": nes_res if nes_res else [], 
                "recolhimentos": rec_res if rec_res else [] 
            }
        except Exception as ex: 
            self.handle_db_error(ex, "buscar dados do Extrato")
            return None
        
    def load_nc_list_for_statement_filter(self):
        """Preenche o seletor de extrato com NCs do banco local."""
        print("Relatórios: A carregar lista de NCs para extrato...")
        try:
            sql = "SELECT id, numero_nc FROM notas_de_credito ORDER BY numero_nc ASC"
            resposta_ncs = database.execute_query(sql)

            self.dropdown_nc_extrato.options = []
            if not resposta_ncs:
                 self.dropdown_nc_extrato.options.append(ft.dropdown.Option(text="Nenhuma NC encontrada", disabled=True))
            else:
                for nc in resposta_ncs:
                    self.dropdown_nc_extrato.options.append(
                        ft.dropdown.Option(key=str(nc['id']), text=nc['numero_nc'])
                    )

            if self.page: self.update() 
        except Exception as ex:
            traceback.print_exc()
            self.handle_db_error(ex, "carregar lista de NCs")
            
    
    # --- LÓGICA DE DOWNLOAD (v8.0 - Mantida) ---
    
    def _executar_download(self, tipo_relatorio, nome_base, dados_para_gerar, button_control_to_update):
        self.progress_ring.visible = True
        button_control_to_update.visible = False 
        self.update()
        
        try:
            self.dados_relatorio_para_salvar = dados_para_gerar
            self.tipo_ficheiro_a_salvar = tipo_relatorio
            
            file_bytes = self._gerar_bytes_do_relatorio()
            
            extensao = "xlsx" if "excel" in tipo_relatorio else "pdf"
            nome_unico = f"{nome_base}_{uuid.uuid4()}.{extensao}"
            
            if not os.path.exists("assets"):
                os.makedirs("assets")
            caminho_servidor = os.path.join("assets", nome_unico)
            
            print(f"A salvar ficheiro público em: {caminho_servidor}")
            with open(caminho_servidor, "wb") as f:
                f.write(file_bytes)
                
            url_download = f"/{nome_unico}" # URL relativa para 'assets/'
            
            button_control_to_update.text = f"Baixar: {nome_unico}"
            button_control_to_update.on_click = lambda e, url=url_download: self.page.launch_url(url)
            button_control_to_update.visible = True
            
            self.show_success_snackbar("Relatório pronto. Clique no botão para baixar.")

        except Exception as e:
            print(f"Erro ao preparar download para {tipo_relatorio}: {e}")
            traceback.print_exc()
            self.show_error(f"Erro ao gerar relatório: {e}")
        
        finally:
            self.dados_relatorio_para_salvar = None
            self.tipo_ficheiro_a_salvar = None
            self.progress_ring.visible = False
            self.update()

    def gerar_relatorio_geral_excel(self, e):
        dados = self.fetch_report_data_geral(e)
        if dados:
            self._executar_download(
                tipo_relatorio="excel_geral",
                nome_base="relatorio_geral_ncs",
                dados_para_gerar=dados,
                button_control_to_update=self.download_button_geral 
            )

    def gerar_relatorio_geral_pdf(self, e):
        dados = self.fetch_report_data_geral(e)
        if dados:
            self._executar_download(
                tipo_relatorio="pdf_geral",
                nome_base="relatorio_geral_ncs",
                dados_para_gerar=dados,
                button_control_to_update=self.download_button_geral
            )

    def gerar_extrato_excel(self, e):
        self.download_button_extrato.visible = False 
        nc_id_selecionada = self.dropdown_nc_extrato.value
        if not nc_id_selecionada: 
            self.page.snack_bar = ft.SnackBar(ft.Text("Selecione uma NC."), bgcolor="orange")
            self.page.snack_bar.open = True; self.page.update()
            return
            
        dados_extrato = self.fetch_report_data_extrato(nc_id_selecionada)
        if dados_extrato:
            nome_base = dados_extrato['nc'].get('numero_nc', 'extrato').replace('/', '_').replace('\\', '_')
            self._executar_download(
                tipo_relatorio="excel_extrato",
                nome_base=f"extrato_{nome_base}",
                dados_para_gerar=dados_extrato,
                button_control_to_update=self.download_button_extrato 
            )

    def gerar_extrato_pdf(self, e):
        self.download_button_extrato.visible = False
        nc_id_selecionada = self.dropdown_nc_extrato.value
        if not nc_id_selecionada: 
            self.page.snack_bar = ft.SnackBar(ft.Text("Selecione uma NC."), bgcolor="orange")
            self.page.snack_bar.open = True; self.page.update()
            return
            
        dados_extrato = self.fetch_report_data_extrato(nc_id_selecionada)
        if dados_extrato:
            nome_base = dados_extrato['nc'].get('numero_nc', 'extrato').replace('/', '_').replace('\\', '_')
            self._executar_download(
                tipo_relatorio="pdf_extrato",
                nome_base=f"extrato_{nome_base}",
                dados_para_gerar=dados_extrato,
                button_control_to_update=self.download_button_extrato
            )

    def _gerar_bytes_do_relatorio(self):
        tipo = self.tipo_ficheiro_a_salvar
        dados = self.dados_relatorio_para_salvar
        
        if not tipo or not dados:
            raise Exception("Dados ou tipo de relatório em falta.")

        print(f"A gerar bytes PRO (v5 - Dashboard Layout) para: {tipo}")

        # --- FUNÇÕES AUXILIARES ---
        def formatar_data_segura(valor):
            if not valor: return ""
            try:
                if hasattr(valor, 'strftime'): return valor.strftime('%d/%m/%Y')
                elif isinstance(valor, str): return datetime.fromisoformat(valor).strftime('%d/%m/%Y')
                return str(valor)
            except: return str(valor)

        # Configuração do Cabeçalho/Rodapé
        def add_header_footer(canvas, doc):
            canvas.saveState()
            w, h = doc.pagesize
            
            # --- 1. LOGO (COM DIAGNÓSTICO DE ERRO) ---
            # Tenta encontrar a logo em múltiplos locais possíveis
            caminhos_tentados = [
                os.path.join(os.getcwd(), "assets", "logo.png"),
                os.path.join(os.getcwd(), "assets", "logo.jpg"),  # Tenta JPG
                os.path.join(os.getcwd(), "assets", "logo.jpeg"), # Tenta JPEG
                "assets/logo.png"
            ]
            
            logo_encontrada = False
            margem_logo = 0
            
            for path in caminhos_tentados:
                if os.path.exists(path):
                    try:
                        # Desenha a logo
                        canvas.drawImage(path, doc.leftMargin, h - 50, width=45, height=45, mask='auto', preserveAspectRatio=True)
                        margem_logo = 55 
                        logo_encontrada = True
                        break
                    except Exception as e:
                        print(f"Erro ao desenhar logo de {path}: {e}")

            # SE NÃO ACHOU A LOGO: Desenha um quadrado vermelho de aviso (Debug Visual)
            if not logo_encontrada:
                print(f"DEBUG LOGO: Não encontrei 'logo.png'. Caminhos testados: {caminhos_tentados}")
                canvas.setFillColor(colors.red)
                canvas.rect(doc.leftMargin, h - 50, 45, 45, fill=1) # Quadrado vermelho
                margem_logo = 55

            # Título do Sistema
            canvas.setFont('Helvetica-Bold', 11) 
            canvas.setFillColor(colors.darkblue)
            canvas.drawString(doc.leftMargin + margem_logo, h - 30, "SISTEMA DE CONTROLE DE NOTAS DE CRÉDITO")
            
            # Data e Hora
            data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
            canvas.setFont('Helvetica', 9)
            canvas.drawRightString(w - doc.rightMargin, h - 30, f"Emitido em: {data_hoje}")
            
            # Linha divisória
            canvas.setStrokeColor(colors.darkblue)
            canvas.setLineWidth(1)
            canvas.line(doc.leftMargin, h - 55, w - doc.rightMargin, h - 55)

            # --- 2. MARCA D'ÁGUA ---
            canvas.setFont('Helvetica-Bold', 100)
            canvas.setFillColor(colors.lightgrey)
            canvas.setFillAlpha(0.15) 
            canvas.drawCentredString(w/2, 60, "SALC")
            canvas.setFillAlpha(1)

            # --- 3. RODAPÉ ---
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.black)
            canvas.drawCentredString(w/2, 15, f"Página {doc.page}")
            
            canvas.restoreState()

        try:
            # === EXCEL GERAL (Mantido) ===
            if tipo == "excel_geral":
                df = pd.DataFrame(dados)
                df = df.rename(columns={ 
                    'numero_nc': 'Número NC', 'nome_secao': 'Seção', 'pi': 'PI', 'natureza_despesa': 'ND', 
                    'status_calculado': 'Status', 'valor_inicial': 'Valor Cota', 'saldo_disponivel': 'Saldo Cota',
                    'valor_total_nc': 'Valor Total NC', 'saldo_disponivel_nc': 'Saldo Total NC',
                    'data_validade_empenho': 'Prazo', 'ug_gestora': 'UG', 'data_recebimento': 'Recebimento', 'observacao': 'Obs' 
                })
                colunas_visiveis = ['Número NC', 'Seção', 'PI', 'ND', 'Status', 'Valor Total NC', 'Saldo Total NC', 'Valor Cota', 'Saldo Cota', 'Prazo', 'Recebimento', 'Obs']
                for col in colunas_visiveis:
                    if col not in df.columns: df[col] = ""
                df = df[colunas_visiveis]
                for col_data in ['Recebimento', 'Prazo']:
                    if col_data in df.columns: df[col_data] = pd.to_datetime(df[col_data], errors='coerce').dt.strftime('%d/%m/%Y')
                for col in ['Valor Total NC', 'Saldo Total NC', 'Valor Cota', 'Saldo Cota']:
                    if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                with io.BytesIO() as file_in_memory:
                    df.to_excel(file_in_memory, index=False, engine='openpyxl')
                    return file_in_memory.getvalue()

            # === PDF GERAL (NOVO LAYOUT DE DUAS COLUNAS NO TOPO) ===
            # === PDF GERAL (ATUALIZADO V6 - Filtros de Zeros + Detalhe NC na Direita) ===
            elif tipo == "pdf_geral":
                with io.BytesIO() as file_in_memory:
                    doc = SimpleDocTemplate(file_in_memory, pagesize=landscape(letter), topMargin=70, bottomMargin=30, leftMargin=20, rightMargin=20)
                    story = []
                    
                    styles = getSampleStyleSheet()
                    style_title = ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=16, spaceAfter=10, textColor=colors.darkblue)
                    
                    # Estilos da Tabela
                    style_center = ParagraphStyle(name='Center', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, leading=11)
                    style_left = ParagraphStyle(name='Left', parent=styles['Normal'], alignment=TA_LEFT, fontSize=9, leading=11)
                    style_right = ParagraphStyle(name='Right', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9, leading=11)
                    style_header_tab = ParagraphStyle(name='TabHeader', parent=style_center, fontName='Helvetica-Bold', textColor=colors.white, fontSize=9)
                    
                    # Estilos do Painel de Resumo
                    style_resumo_item = ParagraphStyle(name='ResumoItem', parent=styles['Normal'], fontSize=9, leading=12)
                    
                    story.append(Paragraph("Relatório Geral de Notas de Crédito", style_title))
                    
                    # --- CÁLCULO INTELIGENTE DOS RESUMOS ---
                    saldo_total_geral = 0
                    resumo_pi = {} 
                    # Nova Estrutura Direita: { 'NomeSecao': { 'NumeroNC': valor_saldo } }
                    resumo_secao_detalhado = {} 

                    for item in dados:
                        saldo_item = float(item.get('saldo_disponivel', 0) or 0)
                        saldo_total_geral += saldo_item
                        
                        # Coleta Esquerda (Origem)
                        pi = str(item.get('pi', 'SEM PI'))
                        nd = str(item.get('natureza_despesa', 'SEM ND'))
                        if pi not in resumo_pi: resumo_pi[pi] = {}
                        if nd not in resumo_pi[pi]: resumo_pi[pi][nd] = 0
                        resumo_pi[pi][nd] += saldo_item
                        
                        # Coleta Direita (Destino com Rastreabilidade)
                        sec = str(item.get('nome_secao', 'GERAL'))
                        nc_num = str(item.get('numero_nc', ''))
                        
                        if sec not in resumo_secao_detalhado: resumo_secao_detalhado[sec] = {}
                        if nc_num not in resumo_secao_detalhado[sec]: resumo_secao_detalhado[sec][nc_num] = 0
                        resumo_secao_detalhado[sec][nc_num] += saldo_item

                    # --- MONTAGEM DO TEXTO (HTML) ---
                    header_html = "<font color='#00008B' size='10'><b>{}</b></font><br/><br/>"

                    # 1. Coluna Esquerda: ORIGEM (Filtrando Zeros)
                    texto_esquerda = header_html.format("ORIGEM (Por PI e ND):")
                    
                    for pi_key in sorted(resumo_pi.keys()):
                        total_pi = sum(resumo_pi[pi_key].values())
                        
                        # MELHORIA 1: Só exibe PI se tiver saldo positivo
                        if total_pi > 0.00:
                            texto_esquerda += f"<b>PI: {pi_key}</b> (Total: {self.formatar_moeda(total_pi)})<br/>"
                            
                            for nd_key in sorted(resumo_pi[pi_key].keys()):
                                val_nd = resumo_pi[pi_key][nd_key]
                                # Só exibe ND se tiver saldo
                                if val_nd > 0.00:
                                    texto_esquerda += f"&nbsp;&nbsp;&nbsp;• ND {nd_key}: {self.formatar_moeda(val_nd)}<br/>"
                            
                            texto_esquerda += "<br/><br/>" # Espaço entre PIs

                    # 2. Coluna Direita: DESTINO (Com NCs Detalhadas)
                    texto_direita = header_html.format("DESTINO (Por Seção):")
                    
                    # Ordena seções por valor total (do maior para o menor)
                    lista_secoes = []
                    for sec, ncs_dict in resumo_secao_detalhado.items():
                        total_sec = sum(ncs_dict.values())
                        lista_secoes.append((sec, total_sec, ncs_dict))
                    
                    lista_secoes.sort(key=lambda x: x[1], reverse=True)
                    
                    for sec_nome, sec_total, ncs_dict in lista_secoes:
                         # Só exibe Seção se tiver saldo
                         if sec_total > 0.00:
                             texto_direita += f"<font size='9'><b>{sec_nome}</b></font>: {self.formatar_moeda(sec_total)}<br/>"
                             
                             # MELHORIA 2: Lista quais NCs compõem esse saldo
                             # Ordena NCs por valor
                             ncs_sorted = sorted(ncs_dict.items(), key=lambda x: x[1], reverse=True)
                             
                             for nc_n, nc_v in ncs_sorted:
                                 if nc_v > 0.00:
                                     # Indentação com seta pequena e cor cinza escuro para diferenciar
                                     texto_direita += f"&nbsp;&nbsp;<font color='#333333' size='8'>» {nc_n}: {self.formatar_moeda(nc_v)}</font><br/>"
                             
                             texto_direita += "<br/>" 

                    # ---------------------------------------------------

                    style_destaque = ParagraphStyle(name='Destaque', parent=styles['Normal'], alignment=TA_LEFT, fontSize=12, textColor=colors.darkblue, fontName='Helvetica-Bold')
                    story.append(Paragraph(f"Saldo Total Disponível: {self.formatar_moeda(saldo_total_geral)}", style_destaque))
                    story.append(Spacer(1, 0.1*inch))

                    # Tabela Resumo Lado a Lado
                    col_resumo_data = [[
                        Paragraph(texto_esquerda, style_resumo_item), 
                        Paragraph(texto_direita, style_resumo_item)
                    ]]
                    t_resumo = Table(col_resumo_data, colWidths=[5.5*inch, 5.0*inch])
                    t_resumo.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('LINEBEFORE', (1,0), (1,-1), 1, colors.lightgrey),
                        ('LEFTPADDING', (1,0), (1,-1), 20),
                    ]))
                    story.append(t_resumo)
                    story.append(Spacer(1, 0.2*inch))
                    
                    # --- TABELA PRINCIPAL (Mantida Igual) ---
                    ncs_agrupadas = {}
                    for item in dados:
                        num = item['numero_nc']
                        if num not in ncs_agrupadas:
                            ncs_agrupadas[num] = item.copy()
                            ncs_agrupadas[num]['lista_secoes'] = []
                        ncs_agrupadas[num]['lista_secoes'].append({
                            'nome': item.get('nome_secao', ''),
                            'val': item.get('valor_inicial', 0),
                            'sal': item.get('saldo_disponivel', 0)
                        })
                    
                    lista_final = list(ncs_agrupadas.values())
                    
                    header = [
                        Paragraph('NC', style_header_tab),
                        Paragraph('Detalhamento por Seção', style_header_tab),
                        Paragraph('PI', style_header_tab),
                        Paragraph('ND', style_header_tab),
                        Paragraph('V. Total', style_header_tab),
                        Paragraph('Saldo Total', style_header_tab),
                        Paragraph('Prazo', style_header_tab),
                        Paragraph('Obs', style_header_tab)
                    ]
                    table_data = [header]
                    row_styles = []
                    
                    for i, nc in enumerate(lista_final):
                        txt_sec = ""
                        for s in nc['lista_secoes']:
                            txt_sec += f"<b>{s['nome']}</b>: {self.formatar_moeda(s['val'])} (Disp: {self.formatar_moeda(s['sal'])})<br/><br/>"
                        txt_sec = txt_sec.rstrip("<br/><br/>")

                        status = nc.get('status_calculado', 'Ativa')
                        bg = colors.white
                        if status == 'Vencida': bg = colors.Color(1, 0.9, 0.9)
                        elif status == 'Sem Saldo': bg = colors.Color(0.95, 0.95, 0.95)
                        elif status == 'Ativa': bg = colors.Color(0.92, 1, 0.92)
                        
                        row_styles.append(('BACKGROUND', (0, i+1), (-1, i+1), bg))
                        
                        row = [
                            Paragraph(str(nc.get('numero_nc')), style_center),
                            Paragraph(txt_sec, style_left),
                            Paragraph(str(nc.get('pi')), style_center),
                            Paragraph(str(nc.get('natureza_despesa')), style_center),
                            Paragraph(self.formatar_moeda(nc.get('valor_total_nc')), style_right),
                            Paragraph(self.formatar_moeda(nc.get('saldo_disponivel_nc')), style_right),
                            Paragraph(formatar_data_segura(nc.get('data_validade_empenho')), style_center),
                            Paragraph(str(nc.get('observacao', '')), style_left)
                        ]
                        table_data.append(row)
                    
                    col_widths = [1.2*inch, 2.5*inch, 1.1*inch, 0.7*inch, 0.9*inch, 0.9*inch, 0.8*inch, 1.9*inch]
                    
                    t = Table(table_data, colWidths=col_widths, repeatRows=1)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                        ('LEFTPADDING', (0,0), (-1,-1), 5),
                        ('RIGHTPADDING', (0,0), (-1,-1), 5),
                        ('TOPPADDING', (0,0), (-1,-1), 5),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ] + row_styles))
                    
                    story.append(t)
                    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
                    return file_in_memory.getvalue()

            # === EXCEL E PDF EXTRATO (Mantidos) ===
            elif tipo == "excel_extrato":
                # (Lógica inalterada)
                df_nc = pd.DataFrame([dados['nc']])
                df_nc = df_nc.rename(columns={ 'numero_nc': 'Número NC', 'pi': 'PI', 'natureza_despesa': 'ND', 'valor_inicial': 'Valor Inicial', 'data_validade_empenho': 'Prazo Empenho', 'ug_gestora': 'UG Gestora', 'data_recebimento': 'Data Recebimento', 'ptres':'PTRES', 'fonte':'Fonte', 'observacao': 'Observação' })
                for col_data in ['Data Recebimento', 'Prazo Empenho']:
                    if col_data in df_nc.columns: df_nc[col_data] = pd.to_datetime(df_nc[col_data], errors='coerce').dt.strftime('%d/%m/%Y')
                secoes_data = []; nes_data = []; rec_data = []
                for s in dados['secoes']: secoes_data.append({'Seção': s['nome'], 'Valor Alocado': s['valor_alocado'], 'Empenhado': s['emp'], 'Recolhido': s['rec'], 'Saldo Real': s['valor_alocado']-s['emp']-s['rec']})
                for ne in dados['nes']: nes_data.append({'NE': ne['numero_ne'], 'Seção': ne['nome_secao'], 'Data': formatar_data_segura(ne['data_empenho']), 'Valor': ne['valor_empenhado'], 'Desc': ne['descricao']})
                for r in dados['recolhimentos']: rec_data.append({'Data': formatar_data_segura(r['data_recolhimento']), 'Seção': r['nome_secao'], 'Valor': r['valor_recolhido'], 'Desc': r['descricao']})
                with io.BytesIO() as file_in_memory:
                    with pd.ExcelWriter(file_in_memory, engine='openpyxl') as writer:
                         df_nc.to_excel(writer, sheet_name='NC Geral', index=False)
                         pd.DataFrame(secoes_data).to_excel(writer, sheet_name='Saldos por Seção', index=False)
                         pd.DataFrame(nes_data).to_excel(writer, sheet_name='Empenhos', index=False)
                         pd.DataFrame(rec_data).to_excel(writer, sheet_name='Recolhimentos', index=False)
                    return file_in_memory.getvalue()

            elif tipo == "pdf_extrato":
                # (Lógica inalterada - Layout Extrato Individual)
                with io.BytesIO() as file_in_memory:
                    doc = SimpleDocTemplate(file_in_memory, pagesize=letter, topMargin=50, leftMargin=40, rightMargin=40)
                    story = []
                    nc = dados['nc']
                    styles = getSampleStyleSheet()
                    style_h2 = ParagraphStyle(name='H2Pro', parent=styles['Heading2'], fontSize=12, textColor=colors.darkblue, spaceAfter=5, spaceBefore=15)
                    style_label = ParagraphStyle(name='Label', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
                    style_val = ParagraphStyle(name='Val', parent=styles['Normal'], fontSize=9)
                    story.append(Paragraph(f"Extrato Detalhado: {nc.get('numero_nc', '')}", styles['Heading1']))
                    dt_rec = formatar_data_segura(nc.get('data_recebimento'))
                    dt_prz = formatar_data_segura(nc.get('data_validade_empenho'))
                    grid_data = [[Paragraph("<b>PI:</b>", style_label), Paragraph(str(nc.get('pi')), style_val), Paragraph("<b>ND:</b>", style_label), Paragraph(str(nc.get('natureza_despesa')), style_val)], [Paragraph("<b>Valor Total:</b>", style_label), Paragraph(self.formatar_moeda(nc.get('valor_inicial')), style_val), Paragraph("<b>Saldo Total:</b>", style_label), Paragraph(self.formatar_moeda(nc.get('saldo_disponivel_nc')), style_val)], [Paragraph("<b>UG:</b>", style_label), Paragraph(str(nc.get('ug_gestora')), style_val), Paragraph("<b>Prazo:</b>", style_label), Paragraph(dt_prz, style_val)],]
                    t_info = Table(grid_data, colWidths=[0.8*inch, 2*inch, 0.8*inch, 2*inch]); t_info.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')])); story.append(t_info)
                    story.append(Spacer(1, 0.1*inch)); story.append(Paragraph(f"<b>Obs:</b> {nc.get('observacao') or 'N/A'}", style_val))
                    LARGURA_TOTAL = 7.5 * inch
                    story.append(Paragraph("Distribuição e Saldos por Seção", style_h2))
                    h_sec = [Paragraph(x, ParagraphStyle(name='HT', parent=styles['Normal'], textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)) for x in ['Seção', 'Alocado', 'Empenhado', 'Recolhido', 'Saldo Real']]
                    d_sec = [h_sec]
                    for s in dados['secoes']:
                        saldo_real = s['valor_alocado'] - s['emp'] - s['rec']
                        row = [Paragraph(s['nome'], style_val), Paragraph(self.formatar_moeda(s['valor_alocado']), style_val), Paragraph(self.formatar_moeda(s['emp']), style_val), Paragraph(self.formatar_moeda(s['rec']), style_val), Paragraph(self.formatar_moeda(saldo_real), ParagraphStyle(name='BoldRight', parent=style_val, fontName='Helvetica-Bold'))]
                        d_sec.append(row)
                    t_sec = Table(d_sec, colWidths=[2.5*inch, 1.25*inch, 1.25*inch, 1.25*inch, 1.25*inch]); t_sec.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkgreen), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)])); story.append(t_sec)
                    story.append(Paragraph("Histórico de Empenhos", style_h2))
                    h_ne = [Paragraph(x, ParagraphStyle(name='HT', textColor=colors.white, fontName='Helvetica-Bold')) for x in ['NE', 'Seção', 'Data', 'Valor', 'Desc']]
                    d_ne = [h_ne]
                    if not dados['nes']: d_ne.append(["Nenhum empenho", "", "", "", ""])
                    else:
                        for ne in dados['nes']:
                            row = [Paragraph(ne['numero_ne'], style_val), Paragraph(ne['nome_secao'], style_val), Paragraph(formatar_data_segura(ne['data_empenho']), style_val), Paragraph(self.formatar_moeda(ne['valor_empenhado']), style_val), Paragraph(ne.get('descricao', ''), style_val)]
                            d_ne.append(row)
                    t_ne = Table(d_ne, colWidths=[1.2*inch, 1.5*inch, 0.8*inch, 1.0*inch, 3.0*inch]); t_ne.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkblue), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.aliceblue])])); story.append(t_ne)
                    story.append(Paragraph("Histórico de Recolhimentos", style_h2))
                    h_rec = [Paragraph(x, ParagraphStyle(name='HT', textColor=colors.white, fontName='Helvetica-Bold')) for x in ['Data', 'Seção', 'Valor', 'Desc']]
                    d_rec = [h_rec]
                    if not dados['recolhimentos']: d_rec.append(["Nenhum recolhimento", "", "", ""])
                    else:
                        for r in dados['recolhimentos']:
                            row = [Paragraph(formatar_data_segura(r['data_recolhimento']), style_val), Paragraph(r['nome_secao'], style_val), Paragraph(self.formatar_moeda(r['valor_recolhido']), style_val), Paragraph(r.get('descricao', ''), style_val)]
                            d_rec.append(row)
                    t_rec = Table(d_rec, colWidths=[1.0*inch, 1.5*inch, 1.2*inch, 3.8*inch]); t_rec.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkorange), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)])); story.append(t_rec)
                    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
                    return file_in_memory.getvalue()
            else: raise Exception(f"Tipo desconhecido: {tipo}")
        except Exception as e:
            print(f"Erro ao gerar bytes: {e}")
            traceback.print_exc()
            raise e
            
# --- FIM DAS ALTERAÇÕES ---

def create_relatorios_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa RelatoriosView como um controlo Flet padrão.
    """
    return RelatoriosView(page, error_modal=error_modal)
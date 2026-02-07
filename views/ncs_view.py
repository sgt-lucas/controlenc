# views/ncs_view.py
# (Versão Refatorada v1.6 - Layout Moderno)
# (Adiciona todos os campos orçamentários ao modal "Quick View")

import flet as ft
import traceback 
from datetime import datetime
# REMOVA: from supabase_client import supabase
# ADICIONE:
import database # Importa o motor do PostgreSQL 17 local

import io       
import httpx    
import os       

# --- IMPORTAÇÕES PARA PDF ---
import pdfplumber
import re
# ----------------------------

class NcsView(ft.Column):
    """
    Representa o conteúdo da aba Notas de Crédito (CRUD).
    (v1.6) Modal "Quick View" exibe todos os dados.
    """
    
    def __init__(self, page, on_data_changed=None, error_modal=None):
        super().__init__()
        self.page = page
        self.id_sendo_editado = None
        self.id_nc_para_recolhimento = None
        self.on_data_changed_callback = on_data_changed
        self.error_modal = error_modal
        
        self.secoes_cache = {} 
        
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        self.file_picker_import = ft.FilePicker(
            on_result=self.on_file_picker_result,
            on_upload=self.on_upload_progress 
        )
        
        self.tabela_ncs = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Número NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Inicial", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Saldo Disp.", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ], 
            rows=[], 
            #expand=True, 
            border=ft.border.all(1, "grey200"), 
            border_radius=8,
        )

        # --- (INÍCIO DA ATUALIZAÇÃO v1.6) ---
        # --- Novo Modal "Quick View" ---
        self.quick_view_title = ft.Text("Detalhes da NC", size=20, weight=ft.FontWeight.BOLD)
        self.qv_status = ft.Text(size=16)
        self.qv_pi_nd = ft.Text(selectable=True)
        # Novos campos para info orçamentária
        self.qv_ptres_fonte = ft.Text(selectable=True)
        self.qv_ug_secao = ft.Text(selectable=True)
        
        self.qv_valor_inicial = ft.Text(selectable=True)
        self.qv_saldo = ft.Text(selectable=True)
        self.qv_percent_empenhado = ft.Text(selectable=True)
        self.qv_prazo = ft.Text(selectable=True)
        self.qv_observacao = ft.Text(selectable=True, max_lines=5, overflow=ft.TextOverflow.ELLIPSIS)

        self.quick_view_modal = ft.AlertDialog(
            modal=True,
            title=self.quick_view_title,
            content=ft.Column(
                [
                    self.qv_status,
                    ft.Divider(),
                    ft.Text("Informação Orçamentária:", weight=ft.FontWeight.BOLD),
                    self.qv_pi_nd,
                    self.qv_ptres_fonte, # Adicionado
                    self.qv_ug_secao,   # Adicionado
                    ft.Divider(),
                    ft.Text("Valores:", weight=ft.FontWeight.BOLD),
                    self.qv_valor_inicial,
                    self.qv_saldo,
                    self.qv_percent_empenhado,
                    ft.Divider(),
                    ft.Text("Prazos:", weight=ft.FontWeight.BOLD),
                    self.qv_prazo,
                    ft.Divider(),
                    ft.Text("Observação:", weight=ft.FontWeight.BOLD),
                    self.qv_observacao,
                ],
                height=450, # Aumenta a altura para os novos campos
                width=500,
                scroll=ft.ScrollMode.ADAPTIVE
            ),
            actions=[
                ft.TextButton("Fechar", on_click=self.close_quick_view_modal)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # --- (FIM DA ATUALIZAÇÃO v1.6) ---

        # --- Modais (Sem alteração) ---
        self.modal_txt_numero_nc = ft.TextField(
            label="Número da NC",
            value="2026NC",
            max_length=12,
            capitalization=ft.TextCapitalization.CHARACTERS,
            helper_text="Exemplo: 2026NC000001"
        )
        # self.modal_dd_secao = ft.Dropdown(label="Seção (Opcional)", options=[ft.dropdown.Option(text="Carregando...", disabled=True)],)
        self.distribuicoes_list = ft.Column(spacing=10)
        
        # Este é o botão que o utilizador clica para criar uma nova linha de seção
        self.btn_add_distribuicao = ft.TextButton("Adicionar Distribuição por Seção", icon="ADD_CIRCLE_OUTLINE", on_click=self.add_distribuicao_row)
        self.modal_txt_data_recebimento = ft.TextField(label="Data Recebimento", hint_text="AAAA-MM-DD", read_only=True, expand=True)
        self.btn_abrir_data_recebimento = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Data Recebimento", on_click=lambda e: self.open_datepicker(self.date_picker_recebimento))
        self.modal_txt_data_validade = ft.TextField(label="Prazo Empenho", hint_text="AAAA-MM-DD", read_only=True, expand=True)
        self.btn_abrir_data_validade = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Prazo Empenho", on_click=lambda e: self.open_datepicker(self.date_picker_validade))
        self.date_picker_recebimento = ft.DatePicker(on_change=self.handle_date_recebimento_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        self.date_picker_validade = ft.DatePicker(on_change=self.handle_date_validade_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        # Usamos 'prefix' (Control) em vez de 'prefix_text' (String) para evitar bugs de cursor
        # Linha 130 aprox.
        self.modal_txt_valor_inicial = ft.TextField(
            label="Valor Inicial",
            prefix_text="R$ ",
            hint_text="Ex: 1500,50",
            # Filtro: permite apenas dígitos e uma vírgula ou ponto decimal
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*[.,]?[0-9]{0,2}$", replacement_string=""),
            on_change=None # Removemos a função format_currency_input
        )
        # No __init__ da NcsView:
        self.modal_rec_secao = ft.Dropdown(
            label="Seção / Cota",
            hint_text="De qual seção retirar o saldo?",
            options=[],
            expand=True
        )
        
        # Linha 180 aprox.
        self.modal_rec_valor = ft.TextField(
            label="Valor Recolhido",
            prefix_text="R$ ",
            hint_text="Ex: 100,00",
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*[.,]?[0-9]{0,2}$", replacement_string=""),
            on_change=None
        )
        self.date_picker_recolhimento = ft.DatePicker(
            on_change=lambda e: setattr(self.modal_rec_data, "value", e.control.value.strftime('%Y-%m-%d')) or self.modal_rec_data.update()
        )
        self.page.overlay.append(self.date_picker_recolhimento)
        self.modal_txt_ptres = ft.TextField(
            label="PTRES",
            max_length=6,
            input_filter=ft.NumbersOnlyInputFilter(),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True
        )
        self.modal_txt_nd = ft.TextField(
            label="ND (Natureza de Despesa)",
            max_length=6,
            input_filter=ft.NumbersOnlyInputFilter(),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True
        )
        self.modal_txt_fonte = ft.TextField(
            label="Fonte",
            max_length=10,
            input_filter=ft.NumbersOnlyInputFilter(),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True
        )
        self.modal_txt_pi = ft.TextField(
            label="Plano Interno (PI)",
            max_length=11,
            capitalization=ft.TextCapitalization.CHARACTERS,
            helper_text="Exemplo: OCS80006000",
            expand=True
        )
        self.modal_txt_ug_gestora = ft.TextField(
            label="UG Gestora",
            max_length=6,
            input_filter=ft.NumbersOnlyInputFilter(),
            keyboard_type=ft.KeyboardType.NUMBER,
            expand=True
        )
        self.modal_txt_observacao = ft.TextField(label="Observação (Opcional)", multiline=True, min_lines=3, max_lines=5)
        self.history_modal_title = ft.Text("Extrato da NC")
        self.history_nes_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, height=150)
        self.history_recolhimentos_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, height=150)
        self.recolhimento_modal_title = ft.Text("Recolher Saldo da NC")
        self.modal_rec_data = ft.TextField(label="Data do Recolhimento", hint_text="AAAA-MM-DD", autofocus=True)
        self.modal_rec_descricao = ft.TextField(label="Descrição (Opcional)")
        self.modal_form_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_form_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_modal)
        self.modal_form_btn_salvar = ft.ElevatedButton("Salvar", on_click=self.save_nc, icon="SAVE")
        self.modal_rec_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_rec_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_recolhimento_modal)
        self.modal_rec_btn_salvar = ft.ElevatedButton("Confirmar Recolhimento", on_click=self.save_recolhimento, icon="KEYBOARD_RETURN")
        self.modal_form = ft.AlertDialog(modal=True, title=ft.Text("Adicionar Nova Nota de Crédito"), content=ft.Column([self.modal_txt_numero_nc, self.distribuicoes_list, self.btn_add_distribuicao, ft.Row([self.modal_txt_data_recebimento, self.btn_abrir_data_recebimento,], spacing=10), ft.Row([self.modal_txt_data_validade, self.btn_abrir_data_validade,], spacing=10), self.modal_txt_valor_inicial, ft.Row([self.modal_txt_ptres, self.modal_txt_nd, self.modal_txt_fonte]), ft.Row([self.modal_txt_pi, self.modal_txt_ug_gestora]), self.modal_txt_observacao,], height=600, width=500, scroll=ft.ScrollMode.ADAPTIVE,), actions=[self.modal_form_loading_ring, self.modal_form_btn_cancelar, self.modal_form_btn_salvar,], actions_alignment=ft.MainAxisAlignment.END,)
        self.history_modal = ft.AlertDialog(modal=True, title=self.history_modal_title, content=ft.Column([ft.Text("Notas de Empenho (NEs) Vinculadas:", weight=ft.FontWeight.BOLD), ft.Container(content=self.history_nes_list, border=ft.border.all(1, "grey300"), border_radius=5, padding=10), ft.Divider(height=10), ft.Text("Recolhimentos de Saldo Vinculados:", weight=ft.FontWeight.BOLD), ft.Container(content=self.history_recolhimentos_list, border=ft.border.all(1, "grey300"), border_radius=5, padding=10),], height=400, width=600,), actions=[ft.TextButton("Fechar", on_click=self.close_history_modal)], actions_alignment=ft.MainAxisAlignment.END,)
        self.recolhimento_modal = ft.AlertDialog(
            modal=True,
            title=self.recolhimento_modal_title,
            content=ft.Column([
                # AQUI ENTRA O NOVO CAMPO EM PRIMEIRO LUGAR:
                self.modal_rec_secao,  # <--- NOVO: O usuário escolhe a seção primeiro

                # Abaixo seguem os campos que já existiam:
                ft.Row([
                    self.modal_rec_data, 
                    ft.IconButton(icon="CALENDAR_MONTH", on_click=lambda _: self.date_picker_rec.pick_date())
                ]),
                self.modal_rec_valor,
                self.modal_rec_descricao
            ], 
            height=350, # <--- ALTERADO: Aumentei de 250 para 350 para caber o novo campo sem apertar
            width=400),
            actions=[
                self.modal_rec_loading_ring, 
                self.modal_rec_btn_cancelar, 
                self.modal_rec_btn_salvar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.confirm_delete_nc_dialog = ft.AlertDialog(modal=True, title=ft.Text("Confirmar Exclusão de Nota de Crédito"), content=ft.Text("Atenção!\nTem a certeza de que deseja excluir esta Nota de Crédito?\nTodas as Notas de Empenho e Recolhimentos vinculados também serão excluídos.\nEsta ação não pode ser desfeita."), actions=[ft.TextButton("Cancelar", on_click=lambda e: self.close_confirm_delete_nc(None)), ft.ElevatedButton("Excluir NC", color="white", bgcolor="red", on_click=self.confirm_delete_nc),], actions_alignment=ft.MainAxisAlignment.END,)

        # --- Filtros (Sem alteração) ---
        self.filtro_pesquisa_nc = ft.TextField(label="Pesquisar por Nº NC", hint_text="Digite parte do número...", expand=True, on_change=self.filtrar_ncs_em_tempo_real, prefix_icon=ft.icons.SEARCH)
        self.filtro_pi = ft.Dropdown(label="Filtrar por PI", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.on_pi_filter_change)
        self.filtro_nd = ft.Dropdown(label="Filtrar por ND", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.load_ncs_data_wrapper)
        self.filtro_status = ft.Dropdown(label="Filtrar por Status", options=[ft.dropdown.Option(text="Ativa", key="Ativa"), ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"), ft.dropdown.Option(text="Vencida", key="Vencida"), ft.dropdown.Option(text="Cancelada", key="Cancelada"),], width=200, on_change=self.load_ncs_data_wrapper)
        self.btn_limpar_filtros = ft.IconButton(icon="CLEAR_ALL", tooltip="Limpar Filtros", on_click=self.limpar_filtros)

        # --- Layout (v1.5) ---
        
        # Card 1: Ações e Filtros
        card_acoes_e_filtros = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Gestão de Notas de Crédito", size=20, weight=ft.FontWeight.W_600),
                                ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            "Adicionar Nova NC", 
                                            icon="ADD", 
                                            on_click=self.open_add_modal
                                        ),
                                        ft.OutlinedButton(
                                            "Importar NC (SIAFI)",
                                            icon="UPLOAD_FILE",
                                            tooltip="Adicionar NC a partir de um PDF do SIAFI",
                                            on_click=self.open_file_picker
                                        )
                                    ],
                                    spacing=10
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        
                        ft.Divider(),
                        ft.Text("Filtros de Exibição:", weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                self.filtro_pesquisa_nc,
                                self.filtro_status, 
                                self.btn_limpar_filtros,
                                ft.IconButton(
                                    icon="REFRESH", 
                                    on_click=self.load_ncs_data_wrapper, 
                                    tooltip="Recarregar e Aplicar Filtros"
                                ),
                                self.progress_ring,
                            ],
                            alignment=ft.MainAxisAlignment.START
                        ),
                        ft.Row(
                            [
                                self.filtro_pi, 
                                self.filtro_nd
                            ]
                        ),
                    ],
                    spacing=15
                )
            )
        )
        
        # Card 2: Tabela de Dados
        card_tabela_ncs = ft.Card(
            elevation=4,
            #expand=True, 
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Container(
                            content=self.tabela_ncs,
                            #expand=True
                        )
                    ],
                    #expand=True
                )
            )
        )

        self.controls = [
            card_acoes_e_filtros,
            card_tabela_ncs
        ]

        self.page.overlay.append(self.modal_form)
        self.page.overlay.append(self.history_modal)
        self.page.overlay.append(self.recolhimento_modal)
        self.page.overlay.append(self.confirm_delete_nc_dialog)
        self.page.overlay.append(self.quick_view_modal) # (v1.5) Adiciona o novo modal
        self.page.overlay.append(self.file_picker_import) 
        self.page.overlay.append(self.date_picker_recebimento) 
        self.page.overlay.append(self.date_picker_validade)   
        self.date_picker_rec = ft.DatePicker(
            on_change=lambda e: setattr(self.modal_rec_data, "value", e.control.value.strftime('%Y-%m-%d')) or self.modal_rec_data.update()
        )
        self.page.overlay.append(self.date_picker_rec)
        
        self.on_mount = self.on_view_mount

    def filtrar_ncs_em_tempo_real(self, e):
        # Chama o seu método de carregamento já existente
        # Ele deve usar o valor de self.txt_busca.value para filtrar
        self.load_ncs_data()
        
    def on_view_mount(self, e):
        print("NcsView: Controlo montado. A carregar dados...")
        self.load_secoes_cache() 
        self.load_filter_options()
        self.load_ncs_data()
        
    # --- (INÍCIO DA ATUALIZAÇÃO v1.6) ---
    def open_quick_view_modal(self, e, nc_obj):
        """Exibe o extrato COMPLETO (Saldos reais, NEs e Recolhimentos) no Quick View."""
        try:
            nc_id = nc_obj.get('id_nc')

            # 1. Busca detalhamento das SEÇÕES com saldo corrigido (Alocado - Empenhado - Recolhido)
            sql_sec = """
                SELECT s.nome, d.valor_alocado, 
                       COALESCE((SELECT SUM(valor_empenhado) FROM notas_de_empenho WHERE id_distribuicao = d.id), 0) as emp,
                       COALESCE((SELECT SUM(valor_recolhido) FROM recolhimentos_de_saldo WHERE id_distribuicao = d.id), 0) as rec
                FROM distribuicao_nc_secoes d
                JOIN secoes s ON s.id = d.id_secao
                WHERE d.id_nc = %s
            """
            fatias = database.execute_query(sql_sec, (nc_id,))
            
            txt_dist = ""
            for f in fatias:
                # CÁLCULO DO SALDO REAL (Ponto 3 resolvido)
                saldo_real = f['valor_alocado'] - f['emp'] - f['rec']
                txt_dist += f"• {f['nome']}: {self.formatar_moeda(f['valor_alocado'])} (Saldo Real: {self.formatar_moeda(saldo_real)})\n"

            # 2. Busca o histórico de EMPENHOS (NEs)
            sql_nes = "SELECT numero_ne, valor_empenhado, data_empenho FROM notas_de_empenho n JOIN distribuicao_nc_secoes d ON n.id_distribuicao = d.id WHERE d.id_nc = %s ORDER BY data_empenho DESC"
            nes_list = database.execute_query(sql_nes, (nc_id,))
            
            txt_nes = ""
            if nes_list:
                for ne in nes_list:
                    dt = ne['data_empenho'].strftime('%d/%m/%Y') if ne['data_empenho'] else "N/A"
                    txt_nes += f"• {ne['numero_ne']} - {self.formatar_moeda(ne['valor_empenhado'])} ({dt})\n"
            else:
                txt_nes = "Nenhum empenho registrado."

            # 3. Busca o histórico de RECOLHIMENTOS
            sql_rec = "SELECT valor_recolhido, data_recolhimento FROM recolhimentos_de_saldo WHERE id_nc = %s ORDER BY data_recolhimento DESC"
            rec_list = database.execute_query(sql_rec, (nc_id,))

            txt_rec = ""
            if rec_list:
                for r in rec_list:
                    dt = r['data_recolhimento'].strftime('%d/%m/%Y') if r['data_recolhimento'] else "N/A"
                    txt_rec += f"• Devolução: {self.formatar_moeda(r['valor_recolhido'])} ({dt})\n"
            else:
                txt_rec = "Nenhum recolhimento registrado."

            # 4. Montagem do Texto no Modal
            self.quick_view_title.value = f"Extrato Completo: {nc_obj['numero_nc']}"
            self.qv_status.value = f"STATUS: {nc_obj['status_calculado']}"
            
            self.qv_pi_nd.value = f"PI: {nc_obj['pi']} | ND: {nc_obj['natureza_despesa']}"
            self.qv_ptres_fonte.value = f"PTRES: {nc_obj['ptres']} | FONTE: {nc_obj['fonte']}"
            
            # Adicionamos os extratos aqui no campo de texto grande
            self.qv_ug_secao.value = (
                f"UG GESTORA: {nc_obj['ug_gestora']}\n\n"
                f"--- SALDOS POR SEÇÃO ---\n{txt_dist}\n"
                f"--- HISTÓRICO DE EMPENHOS ---\n{txt_nes}\n"
                f"--- HISTÓRICO DE RECOLHIMENTOS ---\n{txt_rec}"
            )
            
            self.qv_valor_inicial.value = f"VALOR TOTAL NC: {self.formatar_moeda(nc_obj['valor_total_nc'])}"
            self.qv_saldo.value = f"SALDO DISPONÍVEL GERAL: {self.formatar_moeda(nc_obj['saldo_disponivel_nc'])}"
            
            dt = nc_obj.get('data_validade_empenho')
            self.qv_prazo.value = f"PRAZO LIMITE: {datetime.fromisoformat(str(dt)).strftime('%d/%m/%Y') if dt else 'N/A'}"
            self.qv_observacao.value = nc_obj.get('observacao') or "Sem observação."

            self.quick_view_modal.open = True
            self.page.update()
        except Exception as ex:
            self.show_error(f"Erro ao carregar extrato completo: {ex}")

    def close_quick_view_modal(self, e):
        self.quick_view_modal.open = False
        self.page.update()
        
    def show_error(self, message):
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") 
        
        if "duplicate key value violates unique constraint" in msg and "notas_de_credito_numero_nc_key" in msg:
            self.show_error("Erro: Já existe uma Nota de Crédito com este número (2026NC...).")
        elif "duplicate key value violates unique constraint" in msg:
            self.show_error("Erro: Já existe um registo com este identificador único.")
        elif "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_success_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()
        
    def formatar_moeda(self, valor):
        """Formata valores para exibição na tabela (Ex: R$ 1.500,50)."""
        try: 
            val = float(valor)
            # TÉCNICO: f-string com separador de milhar e substituição manual para padrão BR
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError): 
            return "R$ 0,00"
            
    def formatar_valor_para_campo(self, valor):
        """Retorna o valor como string simples (ex: 1500,50) para o campo."""
        try: 
            val = float(valor)
            return f"{val:.2f}".replace(".", ",")
        except: return ""

    def handle_date_recebimento_change(self, e):
        selected_date = e.control.value
        self.modal_txt_data_recebimento.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_recebimento.update()

    def handle_date_validade_change(self, e):
        selected_date = e.control.value
        self.modal_txt_data_validade.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_validade.update()

    def open_file_picker(self, e):
        try:
            if self.file_picker_import and self.page:
                if self.file_picker_import not in self.page.overlay:
                    print("A re-adicionar file_picker_import ao overlay...")
                    self.page.overlay.append(self.file_picker_import)
                    self.page.update() 
                
                self.file_picker_import.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["pdf"]
                )
                
                self.page.update() 
            else:
                print("ERRO: file_picker_import ou page não estão disponíveis.")
                self.show_error("Erro: O componente de seleção de ficheiro não foi inicializado.")
        except Exception as ex:
            print(f"Erro em open_file_picker: {ex}")
            traceback.print_exc()
            self.show_error(f"Erro ao tentar abrir diálogo: {ex}")
    
    def load_secoes_cache(self):
        """Busca o cache de seções diretamente do PostgreSQL 17 local."""
        print("NcsView: A carregar cache de seções do banco local...")
        try:
            # TÉCNICO: Consulta SQL direta substituindo o supabase.table
            resposta = database.execute_query("SELECT id, nome FROM secoes ORDER BY nome")
            if resposta:
                self.secoes_cache = {secao['id']: secao['nome'] for secao in resposta}
                print(f"NcsView: {len(self.secoes_cache)} seções carregadas no cache.")
        except Exception as ex:
            traceback.print_exc()
            self.handle_db_error(ex, "carregar cache de seções")
            
    def load_secoes_para_dropdown(self):
        try:
            
            if not self.secoes_cache:
                print("NcsView: Cache de seções vazio, a recarregar...")
                self.load_secoes_cache() 

            for secao_id, secao_nome in self.secoes_cache.items():
            
                    ft.dropdown.Option(text=secao_nome, key=secao_id)
        
            
        except Exception as ex:
            print(f"Erro ao carregar seções no dropdown: {ex}")
            self.show_error(f"Erro ao carregar seções: {ex}")
            
    def load_filter_options(self, pi_selecionado=None):
        """Atualiza os dropdowns de filtro usando dados do banco local."""
        try:
            if not self.page: return 
            
            if pi_selecionado is None:
                # Busca PIs Únicos
                pis = database.execute_query("SELECT DISTINCT pi FROM notas_de_credito ORDER BY pi")
                self.filtro_pi.options = [ft.dropdown.Option(text="Todos os PIs", key="")]
                for row in pis:
                    if row['pi']: self.filtro_pi.options.append(ft.dropdown.Option(text=row['pi'], key=row['pi']))
                
                # Busca NDs Únicas
                nds = database.execute_query("SELECT DISTINCT natureza_despesa FROM notas_de_credito ORDER BY natureza_despesa")
                self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key="")]
                for row in nds:
                    if row['natureza_despesa']: self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
            else:
                # Busca NDs vinculadas ao PI (Filtro dependente)
                sql = "SELECT DISTINCT natureza_despesa FROM notas_de_credito WHERE pi = %s ORDER BY natureza_despesa"
                nds = database.execute_query(sql, (pi_selecionado,))
                self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key="")]
                for row in nds:
                    self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
            
            if self.page: self.update()
        except Exception as ex:
            self.handle_db_error(ex, "carregar filtros")
            
    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value and self.filtro_pi.value != "None" else None
        self.filtro_nd.value = None 
        # Se PI for limpo, recarrega todas as NDs globais do cache da sessão
        if not pi_val:
            self.load_filter_options(pi_selecionado=None)
        else:
            self.load_filter_options(pi_selecionado=pi_val) 
        self.load_ncs_data()

    def limpar_filtros(self, e):
        print("A limpar filtros...")
        self.filtro_pesquisa_nc.value = ""
        self.filtro_status.value = None
        self.filtro_pi.value = None
        self.filtro_nd.value = None
        self.load_filter_options(pi_selecionado=None) 
        self.load_ncs_data() 
        self.page.update() 
        
    def load_ncs_data_wrapper(self, e): 
        self.load_ncs_data()
        
    def load_ncs_data(self):
        """Carrega a tabela eliminando duplicatas por espaços e corrigindo filtros."""
        self.progress_ring.visible = True
        self.page.update()
        try:
            # TÉCNICO: Usamos TRIM para ignorar espaços e garantir que NCs iguais sejam unificadas
            sql = "SELECT DISTINCT ON (TRIM(numero_nc)) * FROM ncs_com_saldos WHERE 1=1"
            params = []

            # 1. Filtro de Pesquisa (Texto)
            if self.filtro_pesquisa_nc.value:
                sql += " AND numero_nc ILIKE %s"
                params.append(f"%{self.filtro_pesquisa_nc.value}%")
            
            # 2. Filtros Dropdown (Corrigido: ignora se for vazio ou string "None")
            if self.filtro_status.value and self.filtro_status.value not in ["", "None"]:
                sql += " AND status_calculado = %s"; params.append(self.filtro_status.value)
                
            if self.filtro_pi.value and self.filtro_pi.value not in ["", "None"]:
                sql += " AND pi = %s"; params.append(self.filtro_pi.value)
                
            if self.filtro_nd.value and self.filtro_nd.value not in ["", "None"]:
                sql += " AND natureza_despesa = %s"; params.append(self.filtro_nd.value)

            # OBRIGATÓRIO: O ORDER BY deve seguir o TRIM do DISTINCT
            sql += " ORDER BY TRIM(numero_nc) ASC, data_recebimento DESC"
            
            resposta = database.execute_query(sql, tuple(params))
            
            self.tabela_ncs.rows.clear()
            if resposta:
                for nc in resposta:
                    # CORREÇÃO VITAL: Usar 'id_nc' (que é o que a View retorna agora)
                    actual_id = nc.get('id_nc') 
                    
                    # Busca as seções vinculadas usando o ID correto
                    dist_sql = "SELECT * FROM distribuicao_nc_secoes WHERE id_nc = %s"
                    nc['distribuicao_nc_secoes'] = database.execute_query(dist_sql, (actual_id,))

                    self.tabela_ncs.rows.append(
                        ft.DataRow(cells=[
                            # Passamos o objeto 'nc' completo, que agora tem as seções dentro
                            ft.DataCell(ft.TextButton(text=nc['numero_nc'], on_click=lambda e, o=nc: self.open_quick_view_modal(e, o))),
                            ft.DataCell(ft.Text(nc.get('pi', ''))),
                            ft.DataCell(ft.Text(nc.get('natureza_despesa', ''))),
                            ft.DataCell(ft.Text(self.formatar_moeda(nc.get('valor_total_nc')))),
                            ft.DataCell(ft.Text(self.formatar_moeda(nc.get('saldo_disponivel_nc')), weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.PopupMenuButton(icon="MORE_VERT", items=[
                                ft.PopupMenuItem(text="Editar NC", icon="EDIT", on_click=lambda e, o=nc: self.open_edit_modal(o)),
                                ft.PopupMenuItem(text="Recolher Saldo", icon="KEYBOARD_RETURN", on_click=lambda e, o=nc: self.open_recolhimento_modal(o)),
                                ft.PopupMenuItem(text="Excluir NC", icon="DELETE", on_click=lambda e, o=nc: self.open_confirm_delete_nc(o)),
                            ]))
                        ])
                    )
            else:
                self.tabela_ncs.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Nenhuma NC encontrada.", italic=True)), *[ft.DataCell(ft.Text(""))]*5]))
        except Exception as ex:
            self.handle_db_error(ex, "carregar NCs")
        finally:
            self.progress_ring.visible = False
            self.page.update()
        
    def open_add_modal(self, e):
        print("A abrir modal de ADIÇÃO...")
        self.id_sendo_editado = None 
        self.modal_form.title = ft.Text("Adicionar Nova Nota de Crédito")
        self.modal_form_btn_salvar.text = "Salvar"
        self.modal_form_btn_salvar.icon = "SAVE"
        
        self.load_secoes_para_dropdown()
        
        self.modal_txt_numero_nc.value = "2026NC" 
        self.modal_txt_data_recebimento.value = ""
        self.modal_txt_data_validade.value = ""
        self.modal_txt_valor_inicial.value = ""
        self.modal_txt_ptres.value = ""
        self.modal_txt_nd.value = ""
        self.modal_txt_fonte.value = ""
        self.modal_txt_pi.value = ""
        self.modal_txt_ug_gestora.value = ""
        self.modal_txt_observacao.value = ""
        #self.modal_dd_secao.value = None 
        
        for campo in [self.modal_txt_numero_nc, self.modal_txt_data_recebimento, self.modal_txt_data_validade,
                      self.modal_txt_valor_inicial, self.modal_txt_ptres, self.modal_txt_nd,
                      self.modal_txt_fonte, self.modal_txt_pi, self.modal_txt_ug_gestora,
                      self.modal_txt_observacao]: 
            campo.error_text = None
            
        self.distribuicoes_list.controls.clear()  

        self.modal_form.open = True
        self.page.update()
        self.modal_txt_numero_nc.focus() 

    def open_edit_modal(self, nc):
        """
        Preenche o modal de edição com todos os dados da NC e define o ID de controle.
        Esta função é vital para evitar o erro de 'UniqueViolation' ao salvar.
        """
        print(f"A abrir modal de EDIÇÃO para: {nc['numero_nc']}")
        
        # DEFINIÇÃO DO ID: Garante que o método save_nc saiba que trata-se de um UPDATE
        self.id_sendo_editado = nc.get('id_nc')
        self.nc_em_edicao = nc 
        
        # 1. CARREGAMENTO DOS CAMPOS DE TEXTO E IDENTIFICAÇÃO
        self.modal_txt_numero_nc.value = str(nc.get('numero_nc', ''))
        
        # 2. CARREGAMENTO DOS CAMPOS ORÇAMENTÁRIOS (PTRES, ND, FONTE, PI, UG)
        self.modal_txt_ptres.value = str(nc.get('ptres', ''))
        self.modal_txt_nd.value = str(nc.get('natureza_despesa', ''))
        self.modal_txt_fonte.value = str(nc.get('fonte', ''))
        self.modal_txt_pi.value = str(nc.get('pi', ''))
        self.modal_txt_ug_gestora.value = str(nc.get('ug_gestora', ''))
        
        # 3. CARREGAMENTO DE DATAS E VALORES
        self.modal_txt_data_recebimento.value = str(nc.get('data_recebimento', ''))
        self.modal_txt_data_validade.value = str(nc.get('data_validade_empenho', ''))
        self.modal_txt_valor_inicial.value = self.formatar_valor_para_campo(nc.get('valor_inicial', 0))
        
        # 4. CARREGAMENTO DE OBSERVAÇÕES
        self.modal_txt_observacao.value = str(nc.get('observacao', ''))

        # 5. GERENCIAMENTO DAS SEÇÕES (DISTRIBUIÇÕES)
        self.distribuicoes_list.controls.clear()
        
        # Busca as distribuições vinculadas no objeto NC
        secoes_reais = nc.get('distribuicao_nc_secoes', [])
    
        if secoes_reais:
            for dist in secoes_reais:
                self.add_distribuicao_row(
                    e=None, 
                    secao_id=dist.get('id_secao'), 
                    valor=dist.get('valor_alocado')
                )
        else:
            # Caso não existam seções (NCs legadas), abre uma linha padrão vazia
            self.add_distribuicao_row(None)

        # 6. ATUALIZAÇÃO DA UI DO MODAL
        self.modal_form.title = ft.Text("Editar Nota de Crédito")
        self.modal_form.open = True
        self.page.update()

    def close_modal(self, e):
        self.modal_form.open = False
        self.id_sendo_editado = None 
        self.page.update()

    def save_nc(self, e):
        """Salva NC e Distribuições garantindo que a soma não ultrapasse o total."""
        try:
            # 1. Conversão do valor total (modelo de digitação simples)
            val_texto = self.modal_txt_valor_inicial.value or "0"
            val_ini_total = float(val_texto.replace(".", "").replace(",", "."))
            
            # 2. Validação da soma das seções
            soma_distribuicoes = 0
            distribuicoes_para_salvar = []
            
            for row in self.distribuicoes_list.controls:
                # controle 0 = Dropdown Seção, controle 1 = TextField Valor
                id_secao = row.controls[0].value
                v_texto = row.controls[1].value or "0"
                v_float = float(v_texto.replace(".", "").replace(",", "."))
                
                if id_secao and v_float > 0:
                    soma_distribuicoes += v_float
                    distribuicoes_para_salvar.append((id_secao, v_float))

            # TRAVA DE SEGURANÇA
            if round(soma_distribuicoes, 2) > round(val_ini_total, 2):
                self.show_error(f"Erro: A soma das seções (R$ {soma_distribuicoes:,.2f}) " 
                                f"excede o total da NC (R$ {val_ini_total:,.2f}).")
                return

            user = self.page.session.get("user")
            dados_nc = (
                self.modal_txt_numero_nc.value.strip().upper(), self.modal_txt_data_recebimento.value,
                self.modal_txt_data_validade.value, val_ini_total, self.modal_txt_ptres.value,
                self.modal_txt_nd.value, self.modal_txt_fonte.value, self.modal_txt_pi.value,
                self.modal_txt_ug_gestora.value, self.modal_txt_observacao.value
            )

            # 3. Transação Única: Garante que ou salva tudo ou não salva nada
            if self.id_sendo_editado is None:
                # Nova NC
                sql_ins = """INSERT INTO notas_de_credito 
                             (numero_nc, data_recebimento, data_validade_empenho, valor_inicial, ptres, natureza_despesa, fonte, pi, ug_gestora, observacao) 
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id"""
                res = database.execute_query(sql_ins, dados_nc)
                nc_id = res[0]['id']
                queries = []
            else:
                # Edição: Limpa distribuições antigas e atualiza a NC
                nc_id = self.id_sendo_editado
                queries = [
                    ("UPDATE notas_de_credito SET numero_nc=%s, data_recebimento=%s, data_validade_empenho=%s, valor_inicial=%s, ptres=%s, natureza_despesa=%s, fonte=%s, pi=%s, ug_gestora=%s, observacao=%s WHERE id=%s", 
                     dados_nc + (nc_id,)),
                    ("DELETE FROM distribuicao_nc_secoes WHERE id_nc = %s", (nc_id,))
                ]

            # Adiciona as novas distribuições à transação
            for sid, v_alocado in distribuicoes_para_salvar:
                queries.append(("INSERT INTO distribuicao_nc_secoes (id_nc, id_secao, valor_alocado) VALUES (%s,%s,%s)", 
                                (nc_id, sid, v_alocado)))

            if queries:
                database.execute_transaction(queries)

            self.show_success_snackbar("Nota de Crédito e distribuições salvas com sucesso!")
            self.close_modal(None)
            self.load_ncs_data()
            if self.on_data_changed_callback: self.on_data_changed_callback(None)

        except Exception as ex:
            self.handle_db_error(ex, "salvar NC")

    def _definir_status_nc(self, nc):
        """Calcula o status localmente para evitar erro de coluna inexistente no DB."""
        try:
            hoje = datetime.now().date()
            validade_str = nc.get('data_validade_empenho')
            saldo = float(nc.get('saldo_disponivel', 0))
            if saldo <= 0: 
                return "Sem Saldo"
            if validade_str:
                validade = datetime.fromisoformat(validade_str).date()
                if validade < hoje: 
                    return "Vencida"
            return "Ativa"
        except Exception:
            return "Erro no Cálculo"       
                 
    def open_history_modal(self, nc):
        nc_id = nc.get('id_nc')
        self.history_modal_title.value = f"Extrato: {nc.get('numero_nc')}"
        self.history_nes_list.controls.clear()
        self.history_recolhimentos_list.controls.clear()
        
        try:
            # TÉCNICO: Função auxiliar para tratar datas mistas
            def fmt_d(d):
                if not d: return "N/A"
                return d.strftime('%d/%m/%Y') if not isinstance(d, str) else datetime.fromisoformat(d).strftime('%d/%m/%Y')

            res_nes = database.execute_query("SELECT * FROM notas_de_empenho WHERE id_nc = %s ORDER BY data_empenho DESC", (nc_id,))
            if res_nes:
                for ne in res_nes:
                    self.history_nes_list.controls.append(ft.Text(f"[{fmt_d(ne['data_empenho'])}] - {ne['numero_ne']} - {self.formatar_moeda(ne['valor_empenhado'])}"))

            res_rec = database.execute_query("SELECT * FROM recolhimentos_de_saldo WHERE id_nc = %s ORDER BY data_recolhimento DESC", (nc_id,))
            if res_rec:
                for rec in res_rec:
                    self.history_recolhimentos_list.controls.append(ft.Text(f"[{fmt_d(rec['data_recolhimento'])}] - {self.formatar_moeda(rec['valor_recolhido'])} - {rec['descricao']}"))

            self.history_modal.open = True
            self.page.update()
        except Exception as ex: self.handle_db_error(ex, "carregar extrato")
            
    def close_history_modal(self, e):
        self.history_modal.open = False
        self.page.update()
        
    def open_recolhimento_modal(self, nc):
        """Abre o modal carregando as seções daquela NC."""
        # Usa id_nc conforme padronizamos
        nc_id = nc.get('id_nc')
        if not nc_id:
             self.show_error("Erro: ID da NC não encontrado.")
             return

        self.id_nc_para_recolhimento = nc_id # Mantemos para referência
        self.modal_rec_valor.value = ""
        self.modal_rec_descricao.value = ""
        self.modal_rec_secao.options = [] # Limpa opções antigas

        # Busca as seções/cotas desta NC no banco
        try:
            sql = """
                SELECT d.id, s.nome, d.valor_alocado, 
                       (d.valor_alocado - COALESCE((SELECT SUM(valor_empenhado) FROM notas_de_empenho WHERE id_distribuicao = d.id), 0)
                        - COALESCE((SELECT SUM(valor_recolhido) FROM recolhimentos_de_saldo WHERE id_distribuicao = d.id), 0)) as saldo_real
                FROM distribuicao_nc_secoes d
                JOIN secoes s ON s.id = d.id_secao
                WHERE d.id_nc = %s
            """
            secoes = database.execute_query(sql, (nc_id,))
            
            if secoes:
                for s in secoes:
                    # O value (key) será o ID DA DISTRIBUIÇÃO (d.id)
                    texto = f"{s['nome']} (Disp: {self.formatar_moeda(s['saldo_real'])})"
                    self.modal_rec_secao.options.append(ft.dropdown.Option(text=texto, key=str(s['id'])))
                self.modal_rec_secao.value = None
            else:
                 self.show_error("Erro: Nenhuma distribuição encontrada para esta NC.")
                 return

            self.recolhimento_modal.open = True
            self.page.update()
        except Exception as ex:
            self.handle_db_error(ex, "carregar cotas para recolhimento") 

    def close_recolhimento_modal(self, e):
        self.recolhimento_modal.open = False
        self.id_nc_para_recolhimento = None 
        self.page.update()

    def save_recolhimento(self, e):
        """Salva o recolhimento apenas se houver saldo suficiente na cota."""
        if not self.id_nc_para_recolhimento: return
        
        if not self.modal_rec_secao.value:
            self.show_error("Selecione a Seção/Cota de onde sairá o recurso.")
            return

        try:
            id_distribuicao = int(self.modal_rec_secao.value)
            
            val_raw = self.modal_rec_valor.value or "0"
            valor_recolhimento = float(val_raw.replace(".", "").replace(",", "."))
            
            if valor_recolhimento <= 0:
                self.show_error("O valor do recolhimento deve ser maior que zero.")
                return

            # --- VALIDAÇÃO DE SALDO (CRÍTICA) ---
            # Calcula quanto a seção tem AGORA: (Alocado - Empenhado - Recolhido)
            sql_saldo = """
                SELECT d.valor_alocado - 
                       COALESCE((SELECT SUM(valor_empenhado) FROM notas_de_empenho WHERE id_distribuicao = d.id), 0) -
                       COALESCE((SELECT SUM(valor_recolhido) FROM recolhimentos_de_saldo WHERE id_distribuicao = d.id), 0) as saldo_real
                FROM distribuicao_nc_secoes d
                WHERE d.id = %s
            """
            res = database.execute_query(sql_saldo, (id_distribuicao,))
            saldo_atual = float(res[0]['saldo_real']) if res else 0.0

            if valor_recolhimento > round(saldo_atual, 2):
                self.show_error(f"Saldo insuficiente na cota selecionada!\nSaldo Atual: {self.formatar_moeda(saldo_atual)}\nTentativa: {self.formatar_moeda(valor_recolhimento)}")
                return
            # ------------------------------------

            sql = "INSERT INTO recolhimentos_de_saldo (id_nc, id_distribuicao, data_recolhimento, valor_recolhido, descricao) VALUES (%s, %s, %s, %s, %s)"
            params = (self.id_nc_para_recolhimento, id_distribuicao, self.modal_rec_data.value, valor_recolhimento, self.modal_rec_descricao.value)
            
            database.execute_query(sql, params)
            
            self.show_success_snackbar("Saldo recolhido com sucesso!")
            self.close_recolhimento_modal(None)
            self.load_ncs_data()
            if self.on_data_changed_callback: self.on_data_changed_callback(None)
            
        except Exception as ex:
            self.handle_db_error(ex, "salvar recolhimento")
                 
    def open_confirm_delete_nc(self, nc):
        nc_id = nc.get('id_nc')
        nc_numero = nc.get('numero_nc', 'Desconhecida')
        if not nc_id:
             self.show_error("Erro: ID da NC não encontrado para exclusão.")
             return
        print(f"A pedir confirmação para excluir NC: {nc_numero}")
        self.confirm_delete_nc_dialog.data = nc_id 
        self.page.dialog = self.confirm_delete_nc_dialog 
        self.confirm_delete_nc_dialog.open = True
        self.page.update()

    def close_confirm_delete_nc(self, e):
        self.confirm_delete_nc_dialog.open = False
        self.page.update()

    def confirm_delete_nc(self, e):
        """Exclui a NC e define o utilizador para o log de auditoria."""
        id_para_excluir = self.confirm_delete_nc_dialog.data
        user_atual = self.page.session.get("user") # RESOLVE O ERRO DE NAMEERROR
        try:
            database.registrar_log(user_atual.get('id'), "EXCLUIR_NC", "notas_de_credito", id_para_excluir, "NC removida")
            database.execute_query("DELETE FROM notas_de_credito WHERE id = %s", (id_para_excluir,))
            self.show_success_snackbar("NC excluída com sucesso.")
            self.close_confirm_delete_nc(None)
            self.load_ncs_data() # ATUALIZA A TABELA IMEDIATAMENTE
            if self.on_data_changed_callback: self.on_data_changed_callback(None)
        except Exception as ex:
            self.handle_db_error(ex, "excluir NC")
            
    def on_file_picker_result(self, e: ft.ControlEvent):
        if not e.files: return
        file_name = e.files[0].name
        try:
            upload_url = self.page.get_upload_url(file_name, 120) 
            # Deixe sem o parâmetro method="POST" para usar o padrão do servidor interno
            self.file_picker_import.upload([ft.FilePickerUploadFile(file_name, upload_url)])
            self.progress_ring.visible = True
            self.page.update()
        except Exception as ex: self.show_error(f"Erro: {ex}")

    def on_upload_progress(self, e: ft.ControlEvent):
        """Acompanha o progresso do upload (Versão Segura)."""
        if e.error:
            print(f"on_upload_progress: ERRO: {e.error}")
            self.show_error(f"Erro durante o upload: {e.error}")
            self.progress_ring.visible = False
            self.page.update()
            return
            
        if e.progress < 1.0:
            return

        print("on_upload_progress: Upload 100% concluído.")
        
        file_name = e.file_name
        file_path_no_servidor = os.path.join("uploads", file_name)
        
        print(f"on_upload_progress: A processar ficheiro em: {file_path_no_servidor}")
        
        try:
            if not os.path.exists(file_path_no_servidor):
                print(f"Erro: O caminho '{file_path_no_servidor}' não existe no servidor.")
                self.show_error(f"Erro: Ficheiro não encontrado no servidor após upload.")
                return

            dados_extraidos = self._parse_siafi_pdf(file_path_no_servidor) 
            
            if dados_extraidos:
                print("Dados extraídos com sucesso.")
                self.preencher_modal_com_dados(dados_extraidos)
            else:
                self.show_error("Não foi possível extrair dados do PDF. Verifique o console.")
                
        except Exception as ex:
            print(f"Erro ao processar o PDF pós-upload: {ex}")
            traceback.print_exc()
            self.show_error(f"Erro ao ler o ficheiro PDF: {ex}")
        
        finally: 
            self.progress_ring.visible = False
            self.page.update()

    def _parse_siafi_pdf(self, file_path_or_object): 
        """
        Versão Adaptada v2.0: Suporte ao novo layout SIAFI (Rótulos Empilhados).
        Processa o texto extraído para capturar dados orçamentários e prazos.
        """
        texto_completo = ""
        try:
            with pdfplumber.open(file_path_or_object) as pdf:
                # x_tolerance=5 ajuda a manter palavras de colunas diferentes separadas
                texto_completo = pdf.pages[0].extract_text(layout=True, x_tolerance=5)
        except Exception as e:
            print(f"Erro na leitura física do PDF: {e}")
            return None

        if not texto_completo: return None
        
        dados_nc = {}

        # --- FUNÇÕES AUXILIARES DE TRATAMENTO ---
        def limpar(txt): return re.sub(r'\s+', ' ', txt.strip()) if txt else ""

        def formatar_data_br_para_iso(data_str):
            if not data_str: return None
            # Tenta 04/02/2026 -> 2026-02-04
            match = re.search(r'(\d{2})/(\d{2})/(\d{4})', data_str)
            if match: return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
            return None

        # --- 1. CAPTURA DO NÚMERO DA NC (ANO + NÚMERO) ---
        ano = re.search(r'Ano:\s+(\d{4})', texto_completo)
        num = re.search(r'crédito:\s+(\d+)', texto_completo)
        if ano and num:
            dados_nc['numero_nc'] = f"{ano.group(1)}NC{num.group(1).zfill(6)}"
        
        # --- 2. CAPTURA DA DATA DE EMISSÃO ---
        data_emissao = re.search(r'Emissão:\s+(\d{2}/\d{2}/\d{4})', texto_completo)
        if data_emissao:
            dados_nc['data_recebimento'] = formatar_data_br_para_iso(data_emissao.group(1))

        # --- 3. CAPTURA DA TABELA FINANCEIRA (ORIGEM/DESTINO) ---
        # Padrão: Index PTRES(6) Fonte(10) ND(6) UG(6) PI(S+) Valor
        # Usamos [\S\s]+? para lidar com quebras de linha entre os cabeçalhos e os dados
        padrao_tabela = r'(\d+)\s+(\d{6})\s+(\d{10})\s+(\d{6})\s+(\d{6}|\d{3}\*{3})\s+(\S+)\s+([\d.,]+)'
        match_fin = re.search(padrao_tabela, texto_completo)
        
        if match_fin:
            dados_nc['ptres'] = match_fin.group(2)
            dados_nc['fonte'] = match_fin.group(3)
            dados_nc['nd']    = match_fin.group(4)
            dados_nc['ug_gestora'] = match_fin.group(5).replace('*', '0') # Ajuste para UGs censuradas
            dados_nc['pi']    = match_fin.group(6)
            dados_nc['valor_inicial'] = match_fin.group(7)

        # --- 4. OBSERVAÇÃO E PRAZO DE EMPENHO ---
        obs_match = re.search(r'Descrição:(.*?)(?:Itens de Contabilização|$)', texto_completo, re.DOTALL | re.IGNORECASE)
        if obs_match:
            texto_obs = limpar(obs_match.group(1))
            dados_nc['observacao'] = texto_obs
            
            # Busca Prazo no formato: 27 FEV 26
            meses_map = {'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04', 'MAI': '05', 'JUN': '06', 
                         'JUL': '07', 'AGO': '08', 'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'}
            
            prazo_regex = r'PRAZO DE EMPENHO\s+(\d{1,2})\s+([A-Z]{3})\s+(\d{2,4})'
            m_prazo = re.search(prazo_regex, texto_obs, re.IGNORECASE)
            
            if m_prazo:
                dia = m_prazo.group(1).zfill(2)
                mes = meses_map.get(m_prazo.group(2).upper())
                ano_p = m_prazo.group(3)
                ano_full = f"20{ano_p}" if len(ano_p) == 2 else ano_p
                if mes:
                    dados_nc['data_validade'] = f"{ano_full}-{mes}-{dia}"

        return dados_nc

    def preencher_modal_com_dados(self, dados_nc):
        self.open_add_modal(None)
        
        print("A preencher modal...")
        
        if dados_nc.get('numero_nc'):
            self.modal_txt_numero_nc.value = dados_nc['numero_nc'].upper()
            
        if dados_nc.get('data_recebimento'):
            self.modal_txt_data_recebimento.value = dados_nc['data_recebimento']
        if dados_nc.get('data_validade'):
            self.modal_txt_data_validade.value = dados_nc['data_validade']
            
        if dados_nc.get('valor_inicial'):
            # RESOLVE O ERRO DE UPLOAD: 
            # Apenas limpa pontos de milhar e garante a vírgula decimal
            v_pdf = dados_nc['valor_inicial'].replace("R$", "").strip()
            # Se o PDF vier com '1.500,00', transformamos em '1500,00'
            if "." in v_pdf and "," in v_pdf:
                v_pdf = v_pdf.replace(".", "")
            
            self.modal_txt_valor_inicial.value = v_pdf
            # REMOVIDA a chamada para self.format_currency_input
        if dados_nc.get('ptres'):
            self.modal_txt_ptres.value = dados_nc['ptres']
        if dados_nc.get('nd'):
            self.modal_txt_nd.value = dados_nc['nd']
        if dados_nc.get('fonte'):
            self.modal_txt_fonte.value = dados_nc['fonte']
        if dados_nc.get('pi'):
            self.modal_txt_pi.value = dados_nc['pi']
        if dados_nc.get('ug_gestora'):
            self.modal_txt_ug_gestora.value = dados_nc['ug_gestora']
        if dados_nc.get('observacao'):
            self.modal_txt_observacao.value = dados_nc['observacao']

    def add_distribuicao_row(self, e=None, secao_id=None, valor=None):
        """Cria uma linha com: [Dropdown Seção] [Campo Valor] [Botão Lixo]"""
        
        # 1. Cria o seletor de seção usando as seções que já temos no cache
        dd_secao = ft.Dropdown(
            label="Seção",
            options=[ft.dropdown.Option(text=nome, key=sid) for sid, nome in self.secoes_cache.items()],
            value=secao_id,
            expand=2
        )
        
        # 2. Cria o campo de valor para essa fatia da NC
        txt_valor = ft.TextField(
            label="Valor para esta Seção",
            prefix_text="R$ ",
            value=self.formatar_valor_para_campo(valor) if valor else "",
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*[.,]?[0-9]{0,2}$", replacement_string=""),
            on_change=None, # Sem máscara automática
            expand=1
        )

        # 3. Cria o botão para remover apenas esta linha
        btn_remove = ft.IconButton(
            icon="DELETE_OUTLINE",
            icon_color="red",
            on_click=lambda _: self.remove_distribuicao_row(row_container)
        )

        # Junta tudo numa linha (Row)
        row_container = ft.Row([dd_secao, txt_valor, btn_remove], alignment="start")
        
        # Adiciona à nossa lista vertical
        self.distribuicoes_list.controls.append(row_container)
        self.distribuicoes_list.update()

    def remove_distribuicao_row(self, row_control):
        """Remove a linha específica quando clicar no lixo"""
        self.distribuicoes_list.controls.remove(row_control)
        self.distribuicoes_list.update()        
            
        self.modal_txt_numero_nc.focus()
        self.page.update()
                 
# --- Função de Nível Superior (Obrigatória) ---
def create_ncs_view(page: ft.Page, on_data_changed=None, error_modal=None): 
    """
    Exporta a nossa NcsView como um controlo Flet padrão.
    """
    return NcsView(page, on_data_changed=on_data_changed, error_modal=error_modal)
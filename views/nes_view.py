# views/nes_view.py
# (Versão Refatorada v1.3 - Layout Moderno)
# (Corrige o carregamento do filtro de NC e adiciona scroll à tabela)

import flet as ft
from datetime import datetime
import traceback 
# TÉCNICO: Importa o banco local PostgreSQL 17
import database 

class NesView(ft.Column):
    """
    Representa o conteúdo da aba Notas de Empenho (CRUD).
    (v1.3) Corrige filtro e scroll.
    """
    def __init__(self, page, on_data_changed=None, error_modal=None):
        super().__init__()
        self.page = page
        self.id_ne_sendo_editada = None
        self.on_data_changed_callback = on_data_changed
        self.error_modal = error_modal 
        
        self.saldos_ncs_ativas = {}
        
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        self.tabela_nes = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nº Empenho", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("NC Vinculada", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Data", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Empenhado", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Descrição", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            #expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )

        # --- Modais (Sem alteração) ---
        self.modal_txt_nc = ft.Dropdown(
            label="Selecionar NC (Cota por Seção)",
            hint_text="Escolha a NC para empenhar",
            #expand=True
        )
        
        self.modal_txt_numero_ne = ft.TextField(
            label="Número da NE (6 dígitos)", 
            prefix_text="2026NE",
            input_filter=ft.InputFilter(r"[0-9]"), 
            max_length=6
        )
        
        self.modal_txt_data_empenho = ft.TextField(
            label="Data Empenho", 
            hint_text="AAAA-MM-DD", 
            read_only=True, 
            expand=True
        )
        self.btn_abrir_data_empenho = ft.IconButton(
            icon="CALENDAR_MONTH", 
            tooltip="Selecionar Data", 
            on_click=lambda e: self.open_datepicker(self.date_picker_empenho)
        )
        self.date_picker_empenho = ft.DatePicker(
            on_change=self.handle_date_empenho_change,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        
        self.modal_txt_valor_empenhado = ft.TextField(
            label="Valor Empenhado", 
            prefix_text="R$ ", 
            hint_text="Ex: 1250,00",
            input_filter=ft.InputFilter(allow=True, regex_string=r"^[0-9]*[.,]?[0-9]{0,2}$", replacement_string=""),
            on_change=None # Removemos o format_currency_input
        )
        
        self.modal_txt_descricao = ft.TextField(label="Descrição (Opcional)")
        
        self.modal_form_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_form_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_modal)
        self.modal_form_btn_salvar = ft.ElevatedButton("Salvar", on_click=self.save_ne, icon="SAVE")
        
        self.modal_form = ft.AlertDialog(
            modal=True, title=ft.Text("Adicionar Nova Nota de Empenho"),
            content=ft.Column(
                [
                    self.modal_txt_nc,
                    self.modal_txt_numero_ne,
                    ft.Row(
                        [
                            self.modal_txt_data_empenho, 
                            self.btn_abrir_data_empenho
                        ], 
                        spacing=10
                    ),
                    self.modal_txt_valor_empenhado,
                    self.modal_txt_descricao,
                ], 
                height=450,
                width=500, 
                scroll=ft.ScrollMode.ADAPTIVE,
            ),
            actions=[
                self.modal_form_loading_ring,
                self.modal_form_btn_cancelar,
                self.modal_form_btn_salvar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.confirm_delete_dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirmar Exclusão"),
            content=ft.Text("Tem a certeza de que deseja excluir esta Nota de Empenho? Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_confirm_delete(None)),
                ft.ElevatedButton("Excluir", color="white", bgcolor="red", on_click=self.confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # --- CONTROLOS DE FILTRO ---
        self.filtro_pesquisa_ne = ft.TextField(
            label="Pesquisar por Nº NE", 
            hint_text="Digite...",
            expand=True,
            on_submit=self.load_nes_data_wrapper
        )
        
        # --- NOVO FILTRO DE SEÇÃO ---
        self.filtro_secao = ft.Dropdown(
            label="Filtrar por Seção",
            options=[ft.dropdown.Option(text="Todas as Seções", key="")],
            expand=True,
            on_change=self.on_secao_filter_change # Aciona cascata para filtrar NCs
        )

        self.filtro_nc_vinculada = ft.Dropdown(
            label="Filtrar por NC Vinculada",
            options=[ft.dropdown.Option(text="Todas as NCs", key="")],
            expand=True,
            on_change=self.load_nes_data_wrapper
        )
        
        self.filtro_pi = ft.Dropdown(
            label="Filtrar por PI", 
            options=[ft.dropdown.Option(text="Todos os PIs", key="")], 
            expand=True, 
            on_change=self.load_nes_data_wrapper
        )

        self.filtro_nd = ft.Dropdown(
            label="Filtrar por ND", 
            options=[ft.dropdown.Option(text="Todas as NDs", key="")], 
            expand=True, 
            on_change=self.load_nes_data_wrapper
        )
        
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros",
            on_click=self.limpar_filtros
        )

        # Card 1: Ações e Filtros (Layout Reorganizado)
        card_acoes_e_filtros = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Gestão de Notas de Empenho", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.IconButton(icon="REFRESH", on_click=self.load_nes_data_wrapper, tooltip="Recarregar"),
                                    self.progress_ring,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.ElevatedButton("Adicionar Nova NE", icon="ADD", on_click=self.open_add_modal),
                        
                        ft.Divider(),
                        ft.Text("Filtros de Visualização:", weight=ft.FontWeight.BOLD),
                        
                        # Linha 1: Pesquisa Texto + Seção (O filtro Macro)
                        ft.Row([
                            self.filtro_pesquisa_ne,
                            self.filtro_secao, 
                        ]),
                        
                        # Linha 2: Filtros Específicos
                        ft.Row([
                            self.filtro_nc_vinculada,
                            self.filtro_pi,
                            self.filtro_nd,
                            self.btn_limpar_filtros
                        ]),
                    ],
                    spacing=15
                )
            )
        )
        
        # Card 2: Tabela de Dados
        card_tabela_nes = ft.Card(
            elevation=4,
            #expand=True,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        # --- (CORREÇÃO v1.3 - Scroll) ---
                        # Adiciona um Column com scroll e expand=True
                        # para conter a tabela, permitindo scroll vertical
                        # e horizontal (adaptativo).
                        ft.Column(
                            [self.tabela_nes],
                            scroll=ft.ScrollMode.ADAPTIVE,
                            #expand=True
                        )
                        # --- (FIM DA CORREÇÃO v1.3) ---
                    ],
                    #expand=True
                )
            )
        )
        
        self.controls = [
            card_acoes_e_filtros,
            card_tabela_nes
        ]
        # --- (FIM DA REFATORAÇÃO VISUAL v1.3) ---


        self.page.overlay.append(self.modal_form)
        self.page.overlay.append(self.confirm_delete_dialog)
        self.page.overlay.append(self.date_picker_empenho) 
        
        self.on_mount = self.on_view_mount

    def on_secao_filter_change(self, e):
        """Quando muda a seção, recarrega as NCs daquela seção e os dados."""
        secao_id = self.filtro_secao.value
        self.load_nc_filter_options(secao_id) # Filtra o dropdown de NCs
        self.load_nes_data() # Filtra a tabela

    def load_secoes_filter(self):
        """Carrega todas as seções disponíveis para o filtro macro."""
        try:
            sql = "SELECT id, nome FROM secoes ORDER BY nome"
            res = database.execute_query(sql)
            self.filtro_secao.options = [ft.dropdown.Option(text="Todas as Seções", key="")]
            for r in res:
                self.filtro_secao.options.append(ft.dropdown.Option(text=r['nome'], key=str(r['id'])))
        except Exception as ex:
            print(f"Erro ao carregar seções: {ex}")

    def on_view_mount(self, e):
        """Chamado ao montar a view."""
        self.load_secoes_filter() # Carrega as seções primeiro
        self.load_nc_filter_options()
        self.load_pi_nd_filter_options()
        self.load_nes_data()

    def open_datepicker(self, picker: ft.DatePicker):
        if picker and self.page: 
             if picker not in self.page.overlay:
                 self.page.overlay.append(picker)
                 self.page.update()
             picker.visible = True
             picker.open = True
             self.page.update()

    def handle_date_empenho_change(self, e):
        selected_date = e.control.value
        self.modal_txt_data_empenho.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_empenho.update()

    def show_error(self, message):
        """Exibe o modal de erro global."""
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Trata erros e exibe no snackbar vermelho."""
        msg = str(ex).lower()
        
        if "foreignkeyviolation" in msg:
            mensagem = "Erro: A cota da seção selecionada não é mais válida."
        elif "unique constraint" in msg:
            mensagem = "Erro: Já existe um empenho com este número (2026NE...)."
        elif "check_saldo_insuficiente" in msg: # Caso tenha trigger de saldo no banco
            mensagem = "Erro: Saldo insuficiente na cota desta seção."
        elif "undefinedcolumn" in msg:
            mensagem = "Erro interno: Coluna 'id' migrada para 'id_dist_row'. Atualize o código."
        else:
            mensagem = f"Erro ao {context}: Verifique os dados inseridos."

        # Usa o show_error_snackbar que criamos na etapa anterior
        self.show_error_snackbar(mensagem)

    def show_success_snackbar(self, message):
        """Mostra uma mensagem de sucesso (verde)."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()

    def formatar_moeda(self, valor):
        try:
            val = float(valor)
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"
            
    def formatar_valor_para_campo(self, valor):
        try:
            val = float(valor)
            return f"{val:.2f}".replace(".", ",")
        except (ValueError, TypeError):
            return "0,00"
            
    def format_currency_input(self, e: ft.ControlEvent):
        """Formata o valor monetário_automaticamente ao digitar."""
        try:
            current_value = e.control.value or ""
            digits = "".join(filter(str.isdigit, current_value))

            if not digits:
                e.control.value = ""
                if self.page: self.page.update()
                return

            int_value = int(digits)
            val_float = int_value / 100.0
            formatted_value = f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            if e.control.value != formatted_value:
                e.control.value = formatted_value
                e.control.update()
                
        except Exception as ex:
            print(f"Erro ao formatar moeda: {ex}")

    def load_nc_filter_options(self, id_secao_filtro=None):
        """
        Carrega NCs para o filtro. 
        Se uma seção estiver selecionada, mostra apenas NCs daquela seção.
        """
        try:
            sql = "SELECT id_dist_row, numero_nc, nome_secao FROM ncs_com_saldos"
            params = []
            
            if id_secao_filtro:
                sql += " WHERE id_secao = %s"
                params.append(id_secao_filtro)
                
            sql += " ORDER BY numero_nc"
            
            resposta_ncs = database.execute_query(sql, tuple(params))
            
            self.filtro_nc_vinculada.options = [ft.dropdown.Option(text="Todas as NCs", key="")]
            # Reseta a seleção atual se ela não existir mais na lista filtrada
            self.filtro_nc_vinculada.value = "" 
            
            if resposta_ncs:
                for nc in resposta_ncs:
                    self.filtro_nc_vinculada.options.append(
                        ft.dropdown.Option(key=str(nc['id_dist_row']), text=f"{nc['numero_nc']} ({nc['nome_secao']})")
                    )
            
            if self.page: self.filtro_nc_vinculada.update()

        except Exception as ex:
            print(f"Erro filtro NC: {ex}")

    def load_pi_nd_filter_options(self):
        """Carrega PIs e NDs únicos presentes na view."""
        try:
            # PIs
            pis = database.execute_query("SELECT DISTINCT pi FROM ncs_com_saldos ORDER BY pi")
            self.filtro_pi.options = [ft.dropdown.Option(text="Todos os PIs", key="")]
            for row in pis:
                if row['pi']: self.filtro_pi.options.append(ft.dropdown.Option(text=row['pi'], key=row['pi']))
            
            # NDs
            nds = database.execute_query("SELECT DISTINCT natureza_despesa FROM ncs_com_saldos ORDER BY natureza_despesa")
            self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key="")]
            for row in nds:
                if row['natureza_despesa']: self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
                
            if self.page: self.filtro_pi.update(); self.filtro_nd.update()
        except Exception:
            pass

    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_pi_nd_filter_options(pi_selecionado=pi_val) 
        self.load_nes_data() 

    def load_nes_data_wrapper(self, e):
        self.load_nes_data()

    def load_nes_data(self):
        """Carrega NEs aplicando todos os filtros (Seção, NC, PI, ND, Pesquisa)."""
        self.progress_ring.visible = True
        if self.page: self.page.update()

        try:
            # JOIN Correto: NE (id_distribuicao) -> View (id_dist_row)
            sql = """
                SELECT ne.*, v.numero_nc, v.nome_secao, v.pi, v.natureza_despesa
                FROM notas_de_empenho ne
                JOIN ncs_com_saldos v ON ne.id_distribuicao = v.id_dist_row
                WHERE 1=1
            """
            params = []

            # 1. Filtro de Texto (Número NE)
            if self.filtro_pesquisa_ne.value:
                sql += " AND ne.numero_ne ILIKE %s"
                params.append(f"%{self.filtro_pesquisa_ne.value}%")
            
            # 2. Filtro de Seção (O NOVO)
            if self.filtro_secao.value:
                sql += " AND v.id_secao = %s"
                params.append(int(self.filtro_secao.value))

            # 3. Filtro de NC Vinculada
            if self.filtro_nc_vinculada.value:
                sql += " AND ne.id_distribuicao = %s" # Nota: Filtramos pelo ID da cota
                params.append(int(self.filtro_nc_vinculada.value))

            # 4. Filtro de PI
            if self.filtro_pi.value:
                sql += " AND v.pi = %s"
                params.append(self.filtro_pi.value)

            # 5. Filtro de ND
            if self.filtro_nd.value:
                sql += " AND v.natureza_despesa = %s"
                params.append(self.filtro_nd.value)

            sql += " ORDER BY ne.created_at DESC"
            
            resposta = database.execute_query(sql, tuple(params))

            self.tabela_nes.rows.clear()
            
            if resposta:
                for ne in resposta:
                    texto_nc = f"{ne['numero_nc']} ({ne['nome_secao']})"
                    data_emp = datetime.fromisoformat(str(ne['data_empenho'])).strftime('%d/%m/%Y')

                    self.tabela_nes.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(ne['numero_ne'])),
                                ft.DataCell(ft.Text(texto_nc)), # Mostra qual seção está vinculada
                                ft.DataCell(ft.Text(data_emp)),
                                ft.DataCell(ft.Text(self.formatar_moeda(ne['valor_empenhado']))),
                                ft.DataCell(ft.Text(ne.get('descricao') or "")),
                                ft.DataCell(ft.Row([
                                    ft.IconButton("EDIT", icon_color="blue700", on_click=lambda e, o=ne: self.open_edit_modal(o)),
                                    ft.IconButton("DELETE", icon_color="red700", on_click=lambda e, o=ne: self.open_confirm_delete(o))
                                ]))
                            ]
                        )
                    )
            else:
                self.tabela_nes.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Nenhum empenho encontrado para estes filtros.", italic=True)), *[ft.DataCell(ft.Text(""))]*5]))

        except Exception as ex:
            self.handle_db_error(ex, "carregar tabela de NEs")
        finally: 
            self.progress_ring.visible = False
            if self.page: self.page.update()
            
    def limpar_filtros(self, e):
        """Limpa tudo, incluindo a seção."""
        self.filtro_pesquisa_ne.value = ""
        self.filtro_secao.value = ""
        self.filtro_nc_vinculada.value = ""
        self.filtro_pi.value = ""
        self.filtro_nd.value = ""
        
        # Recarrega filtros completos
        self.load_nc_filter_options(None) 
        self.load_nes_data()

    def carregar_ncs_para_dropdown_modal(self):
        """
        Popula o dropdown apenas com cotas que têm saldo positivo (> 0).
        Isso limpa a lista e evita erros operacionais.
        """
        try:
            # TÉCNICO: Adicionamos 'AND saldo_disponivel > 0' para esconder as zeradas
            sql = """
                SELECT id_dist_row, numero_nc, nome_secao, saldo_disponivel 
                FROM ncs_com_saldos 
                WHERE status_calculado = 'Ativa' 
                AND saldo_disponivel > 0 
                ORDER BY numero_nc
            """
            resposta = database.execute_query(sql)

            self.modal_txt_nc.options.clear()
            
            if not resposta:
                # Se for edição, pode ser que a única cota disponível seja a atual (que pode estar zerada/comprometida)
                # Mas para adição, isso informa que não há saldo.
                if not self.id_ne_sendo_editada:
                    print("Aviso: Nenhuma NC com saldo positivo encontrada.")
                return False

            for item in resposta:
                label = f"{item['numero_nc']} ({item['nome_secao']}) - Disp: {self.formatar_moeda(item['saldo_disponivel'])}"
                self.modal_txt_nc.options.append(ft.dropdown.Option(text=label, key=str(item['id_dist_row'])))
            
            if self.modal_txt_nc.page:
                self.modal_txt_nc.update()
            return True
            
        except Exception as ex:
            print(f"Erro ao carregar NCs para modal: {ex}")
            return False

    def open_add_modal(self, e):
        print("A abrir modal de ADIÇÃO de NE...")
        # Tenta carregar as NCs. Se falhar ou não houver, ele avisará.
        if self.carregar_ncs_para_dropdown_modal():
            self.id_sendo_editado = None
            self.modal_txt_numero_ne.value = ""
            self.modal_txt_valor_empenhado.value = ""
            self.modal_txt_nc.value = None # Limpa a seleção anterior
            
            self.modal_form.open = True
            self.page.update()
        else:
            self.show_error("Não foi possível abrir o modal: Verifique se existem NCs com saldo e dentro do prazo.")

    def open_edit_modal(self, ne):
        print(f"A abrir modal de EDIÇÃO para NE: {ne['numero_ne']}")
        self.carregar_ncs_para_dropdown_modal() 
        self.id_ne_sendo_editada = ne['id']
        self.modal_form.title = ft.Text(f"Editar NE: {ne['numero_ne']}")
        self.modal_form_btn_salvar.text = "Atualizar"
        self.modal_form_btn_salvar.icon = "UPDATE"
        
        self.modal_txt_nc.value = ne['id_distribuicao'] 
        
        numero_ne_sem_prefixo = ne.get('numero_ne', '').upper().replace("2026NE", "")
        self.modal_txt_numero_ne.value = numero_ne_sem_prefixo
        
        self.modal_txt_data_empenho.value = ne['data_empenho']
        self.modal_txt_valor_empenhado.value = self.formatar_valor_para_campo(ne['valor_empenhado'])
        self.modal_txt_descricao.value = ne['descricao']
        for campo in [self.modal_txt_nc, self.modal_txt_numero_ne, self.modal_txt_data_empenho, self.modal_txt_valor_empenhado]:
            campo.error_text = None
        self.modal_form.open = True
        self.page.update()

    def close_modal(self, e):
        self.modal_form.open = False
        self.id_ne_sendo_editada = None 
        self.page.update()

    def save_ne(self, e):
        """Grava a NE validando se há saldo disponível na cota da seção."""
        try:
            if not self.modal_txt_nc.value:
                self.show_error_snackbar("Selecione uma NC/Cota para empenhar.")
                return

            # 1. Preparação dos dados
            id_dist = int(self.modal_txt_nc.value)
            v_raw = self.modal_txt_valor_empenhado.value or "0"
            valor_novo_empenho = float(v_raw.replace(".", "").replace(",", "."))
            numero_ne_completo = f"2026NE{self.modal_txt_numero_ne.value.strip()}"

            # 2. Validação de Saldo (Gargalo 4)
            # Busca o saldo atual da fatia na View
            sql_check = "SELECT saldo_disponivel FROM ncs_com_saldos WHERE id_dist_row = %s"
            res = database.execute_query(sql_check, (id_dist,))
            saldo_atual = float(res[0]['saldo_disponivel']) if res else 0

            # Se for edição, devolvemos o valor antigo ao saldo para validar o novo valor
            if self.id_ne_sendo_editada:
                res_ant = database.execute_query("SELECT valor_empenhado FROM notas_de_empenho WHERE id = %s", (self.id_ne_sendo_editada,))
                valor_antigo = float(res_ant[0]['valor_empenhado']) if res_ant else 0
                saldo_atual += valor_antigo

            if valor_novo_empenho > round(saldo_atual, 2):
                self.show_error_snackbar(f"Saldo Insuficiente! Disponível na seção: R$ {saldo_atual:,.2f}")
                return

            # 3. Definição da variável 'dados' (Resolve o NameError)
            dados = (
                numero_ne_completo,
                valor_novo_empenho,
                id_dist,
                self.modal_txt_data_empenho.value,
                self.modal_txt_descricao.value
            )

            # 4. Execução no Banco
            if self.id_ne_sendo_editada:
                sql = "UPDATE notas_de_empenho SET numero_ne=%s, valor_empenhado=%s, id_distribuicao=%s, data_empenho=%s, descricao=%s WHERE id=%s"
                database.execute_query(sql, dados + (self.id_ne_sendo_editada,))
            else:
                sql = "INSERT INTO notas_de_empenho (numero_ne, valor_empenhado, id_distribuicao, data_empenho, descricao) VALUES (%s,%s,%s,%s,%s)"
                database.execute_query(sql, dados)

            self.show_success_snackbar("Nota de Empenho salva com sucesso!")
            self.close_modal(None)
            self.load_nes_data()
            if self.on_data_changed_callback: self.on_data_changed_callback(None)

        except Exception as ex:
            self.handle_db_error(ex, "salvar NE")
            
    def open_confirm_delete(self, ne):
        """Abre o diálogo de confirmação."""
        self.confirm_delete_dialog.data = ne['id'] 
        self.page.dialog = self.confirm_delete_dialog 
        self.confirm_delete_dialog.open = True
        self.page.update()

    def close_confirm_delete(self, e):
        """Fecha o diálogo de confirmação."""
        self.confirm_delete_dialog.open = False
        self.page.update()

    def confirm_delete(self, e):
        """Exclui o empenho permanentemente do banco local (Sem Supabase)."""
        id_para_excluir = self.confirm_delete_dialog.data
        try:
            # Executa a exclusão direta no PostgreSQL local
            database.execute_query("DELETE FROM notas_de_empenho WHERE id = %s", (id_para_excluir,))
            
            # Feedback e atualização
            self.show_success_snackbar("Nota de Empenho excluída com sucesso.")
            self.close_confirm_delete(None)
            self.load_nes_data()
            
            # Atualiza o Dashboard e a aba de NCs para liberar o saldo
            if self.on_data_changed_callback: 
                self.on_data_changed_callback(None)
                
        except Exception as ex:
            self.handle_db_error(ex, "excluir NE")


    def show_error_snackbar(self, message):
        """Exibe uma mensagem de erro em um Snackbar vermelho."""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor="red-700",
            action="OK"
        )
        self.page.snack_bar.open = True
        self.page.update()

def create_nes_view(page: ft.Page, on_data_changed=None, error_modal=None): 
    """
    Exporta a nossa NesView como um controlo Flet padrão.
    """
    return NesView(page, on_data_changed=on_data_changed, error_modal=error_modal)
# views/nes_view.py
# (Versão Refatorada v1.3 - Layout Moderno)
# (Corrige o carregamento do filtro de NC e adiciona scroll à tabela)

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime
import traceback 

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
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )

        # --- Modais (Sem alteração) ---
        self.modal_txt_nc = ft.Dropdown(
            label="Selecionar NC (Cota por Seção)",
            hint_text="Escolha a NC para empenhar",
            expand=True
        )
        
        self.modal_txt_numero_ne = ft.TextField(
            label="Número da NE (6 dígitos)", 
            prefix_text="2026NE",
            input_filter=ft.InputFilter(r"[0-9]"), 
            max_length=6,                           
            keyboard_type=ft.KeyboardType.NUMBER
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
            prefix="R$", 
            on_change=self.format_currency_input, 
            keyboard_type=ft.KeyboardType.NUMBER   
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
        
        # --- CONTROLOS DE FILTRO (Sem alteração) ---
        self.filtro_pesquisa_ne = ft.TextField(
            label="Pesquisar por Nº NE", 
            hint_text="Digite parte do número...",
            expand=True,
            on_submit=self.load_nes_data_wrapper
        )
        self.filtro_nc_vinculada = ft.Dropdown(
            label="Filtrar por NC Vinculada",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True,
            on_change=self.load_nes_data_wrapper
        )
        
        self.filtro_pi = ft.Dropdown(
            label="Filtrar por PI", 
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)], 
            expand=True, 
            on_change=self.on_pi_filter_change
        )
        self.filtro_nd = ft.Dropdown(
            label="Filtrar por ND", 
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)], 
            expand=True, 
            on_change=self.load_nes_data_wrapper
        )
        
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros",
            on_click=self.limpar_filtros
        )

        # --- (INÍCIO DA REFATORAÇÃO VISUAL v1.3) ---
        
        # Card 1: Ações e Filtros
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
                                    ft.IconButton(
                                        icon="REFRESH", 
                                        on_click=self.load_nes_data_wrapper, 
                                        tooltip="Recarregar e Aplicar Filtros"
                                    ),
                                    self.progress_ring,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.ElevatedButton("Adicionar Nova NE", icon="ADD", on_click=self.open_add_modal),
                        
                        ft.Divider(),
                        ft.Text("Filtros de Exibição:", weight=ft.FontWeight.BOLD),
                        ft.Row([
                            self.filtro_pesquisa_ne,
                            self.filtro_nc_vinculada,
                        ]),
                        ft.Row([
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
            expand=True,
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
                            expand=True
                        )
                        # --- (FIM DA CORREÇÃO v1.3) ---
                    ],
                    expand=True
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
        
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("NesView: Controlo montado. A carregar dados...")
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
        """Traduz erros comuns do Supabase/PostgREST para mensagens amigáveis."""
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") # Manter no log
        
        if "duplicate key value violates unique constraint" in msg and "notas_de_empenho_numero_ne_key" in msg:
            self.show_error("Erro: Já existe uma Nota de Empenho com este número (2026NE...).")
        elif "duplicate key value violates unique constraint" in msg:
            self.show_error("Erro: Já existe um registo com este identificador único.")
        elif "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

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

    def load_nc_filter_options(self):
        if not self.page: return
        ncs_cache = self.page.session.get("cache_ncs_lista")
        if ncs_cache:
            self.filtro_nc_vinculada.options = [ft.dropdown.Option(text="Todas as NCs", key=None)] + \
                                               [ft.dropdown.Option(key=nc['id'], text=nc['numero_nc']) for nc in ncs_cache]
            self.update()
            return
        ncs_cache = self.page.session.get("cache_ncs_lista")
        if ncs_cache:
            print("NEs: A carregar NCs para filtro via Cache.")
            self.filtro_nc_vinculada.options = [ft.dropdown.Option(text="Todas as NCs", key=None)]
            for nc in ncs_cache:
                self.filtro_nc_vinculada.options.append(ft.dropdown.Option(key=nc['id'], text=nc['numero_nc']))
            self.update()
            return
        print("NEs: A carregar NCs para o filtro...")
        try:
            # --- (CORREÇÃO v1.3 - Eficiência) ---
            # Troca a consulta da view 'ncs_com_saldos' pela tabela 'notas_de_credito'
            resposta_ncs = supabase.table('ncs_com_saldo').select('id, numero_nc').order('numero_nc', desc=False).execute()
            # --- (FIM DA CORREÇÃO v1.3) ---

            self.filtro_nc_vinculada.options.clear()
            self.filtro_nc_vinculada.options.append(ft.dropdown.Option(text="Todas as NCs", key=None))
            
            if resposta_ncs.data:
                for nc in resposta_ncs.data:
                    self.filtro_nc_vinculada.options.append(
                        ft.dropdown.Option(key=nc['id'], text=nc['numero_nc'])
                    )
            else:
                 self.filtro_nc_vinculada.options.append(ft.dropdown.Option(text="Nenhuma NC encontrada", disabled=True))

            print("NEs: Opções de filtro NC carregadas.")
            self.update()

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO NES [load_nc_filter_options] ---")
            traceback.print_exc()
            print("----------------------------------------------------------------")
            
            print(f"Erro ao carregar NCs para filtro: {ex}")
            self.handle_db_error(ex, "carregar filtros de NC")

    def load_pi_nd_filter_options(self, pi_selecionado=None):
        try:
            if pi_selecionado is None:
                print("NEs: A carregar opções de filtro (PIs e NDs)...")
                pis = supabase.rpc('get_distinct_pis').execute()
                self.filtro_pi.options.clear()
                self.filtro_pi.options.append(ft.dropdown.Option(text="Todos os PIs", key=None)) 
                if pis.data:
                    for pi in sorted(pis.data): 
                        if pi: self.filtro_pi.options.append(ft.dropdown.Option(text=pi, key=pi))
                
                nds = supabase.rpc('get_distinct_nds').execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None)) 
                if nds.data:
                    for nd in sorted(nds.data): 
                        if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("NEs: Opções de filtro PI/ND iniciais carregadas.")
            else:
                print(f"NEs: A carregar NDs para o PI: {pi_selecionado}...")
                self.filtro_nd.disabled = True 
                self.filtro_nd.update()
                nds = supabase.rpc('get_distinct_nds_for_pi', {'p_pi': pi_selecionado}).execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                         if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("NEs: Filtro ND atualizado.")
                
            self.filtro_nd.disabled = False 
            
            if pi_selecionado is None:
                self.update() 
                
        except Exception as ex: 
            print("--- ERRO CRÍTICO (TRACEBACK) NO NES [load_pi_nd_filter_options] ---")
            traceback.print_exc()
            print("---------------------------------------------------------------------")
            
            print(f"Erro ao carregar opções de filtro PI/ND: {ex}")
            self.handle_db_error(ex, "carregar filtros PI/ND")

    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_pi_nd_filter_options(pi_selecionado=pi_val) 
        self.load_nes_data() 

    def load_nes_data_wrapper(self, e):
        self.load_nes_data()

    def load_nes_data(self):
        print("NEs: A carregar dados com filtros...")
        self.progress_ring.visible = True
        if self.page:
            self.page.update()

        try:
            # 1. Ajuste da Query: Buscamos apenas os dados da tabela de empenho
            # Removemos o select('*, ncs_com_saldo(...)') que causava o erro
            query = supabase.table('notas_de_empenho').select('*')

            # --- APLICAÇÃO DOS FILTROS ---
            if self.filtro_pesquisa_ne.value:
                query = query.ilike('numero_ne', f"%{self.filtro_pesquisa_ne.value}%")
            
            # O filtro de NC agora usa a coluna id_distribuicao
            if self.filtro_nc_vinculada.value:
                query = query.eq('id_distribuicao', self.filtro_nc_vinculada.value)
            
            # Nota: Filtros de PI e ND exigem lógica da View. 
            # Por enquanto, vamos carregar as NEs e filtrar a exibição.

            resposta = query.order('created_at', desc=True).execute()

            self.tabela_nes.rows.clear()
            
            if resposta.data:
                for ne in resposta.data:
                    # 2. Busca manual dos detalhes da NC/Seção na View para cada NE
                    # Isso resolve o erro 'Could not find a relationship'
                    detalhes_nc = supabase.table('ncs_com_saldos') \
                        .select('numero_nc, nome_secao') \
                        .eq('id', ne['id_distribuicao']) \
                        .execute()
                    
                    if detalhes_nc.data:
                        info = detalhes_nc.data[0]
                        # Exemplo: 2025NC123456 (Seção TI)
                        texto_nc = f"{info['numero_nc']} ({info['nome_secao']})"
                    else:
                        texto_nc = "NC/Seção não encontrada"

                    # Formatação de Data
                    try:
                        data_emp = datetime.fromisoformat(ne['data_empenho']).strftime('%d/%m/%Y')
                    except:
                        data_emp = ne['data_empenho']

                    # Adiciona a linha na tabela
                    self.tabela_nes.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(ne['numero_ne'])),
                                ft.DataCell(ft.Text(texto_nc)),
                                ft.DataCell(ft.Text(data_emp)),
                                ft.DataCell(ft.Text(self.formatar_moeda(ne['valor_empenhado']))),
                                ft.DataCell(ft.Text(ne.get('descricao', '') or "")),
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(
                                            icon="EDIT", 
                                            tooltip="Editar NE",
                                            icon_color="blue700",
                                            on_click=lambda e, ne_obj=ne: self.open_edit_modal(ne_obj)
                                        ),
                                        ft.IconButton(
                                            icon="DELETE", 
                                            tooltip="Excluir NE",
                                            icon_color="red700",
                                            on_click=lambda e, ne_obj=ne: self.open_confirm_delete(ne_obj)
                                        )
                                    ])
                                ),
                            ]
                        )
                    )
            else:
                self.tabela_nes.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Nenhuma Nota de Empenho encontrada.", italic=True)),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")),
                    ])
                )
            
            print("NEs: Dados carregados com sucesso.")

        except Exception as ex:
            print("--- ERRO NO NES [load_nes_data] ---")
            print(f"Detalhes: {ex}")
            self.handle_db_error(ex, "carregar Notas de Empenho")
        
        finally: 
            self.progress_ring.visible = False
            if self.page:
                self.page.update()

    def limpar_filtros(self, e):
        print("NEs: A limpar filtros...")
        self.filtro_pesquisa_ne.value = ""
        self.filtro_nc_vinculada.value = None
        self.filtro_pi.value = None     
        self.filtro_nd.value = None     
        self.load_pi_nd_filter_options(pi_selecionado=None) 
        self.load_nes_data()
        self.page.update()

    def carregar_ncs_para_dropdown_modal(self):
        try:
            # 1. Busca os dados da VIEW que criamos na Etapa 1
            # Importante: O status deve ser 'Ativa' (Saldo > 0 e dentro do prazo)
            resposta = supabase.table('ncs_com_saldos') \
                .select('id, numero_nc, nome_secao, saldo_disponivel') \
                .eq('status_calculado', 'Ativa') \
                .execute()

            # 2. Verificação de segurança para o componente
            if not hasattr(self, 'modal_txt_nc'):
                print("ERRO CRÍTICO: O componente self.modal_txt_nc não foi definido no __init__")
                return False

            self.modal_txt_nc.options.clear()
            
            if not resposta.data:
                print("Aviso: Nenhuma NC com saldo encontrada no banco.")
                return False

            for item in resposta.data:
                # Exibição clara: Número da NC + Seção + Saldo
                texto_label = f"{item['numero_nc']} ({item['nome_secao']}) - Saldo: R$ {item['saldo_disponivel']:,.2f}"
                
                self.modal_txt_nc.options.append(
                    ft.dropdown.Option(
                        text=texto_label, 
                        key=str(item['id']) # ID da LINHA DE DISTRIBUIÇÃO
                    )
                )
            
            self.modal_txt_nc.update()
            return True
            
        except Exception as ex:
            print(f"Erro ao carregar NCs para o empenho: {ex}")
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
        
        self.modal_txt_nc.value = ne['id_nc'] 
        
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
        try:
            print(f"DEBUG: ID selecionado no dropdown: {self.modal_txt_nc.value}")
            
            # 1. Validação inicial
            if not self.modal_txt_nc.value:
                self.show_error("Selecione uma NC/Cota para realizar o empenho.")
                return

            # 2. Busca dados da VIEW para validar status e saldo
            check_nc = supabase.table('ncs_com_saldos') \
                .select('*') \
                .eq('id', self.modal_txt_nc.value) \
                .execute()
            
            print(f"DEBUG: Dados retornados do Banco: {check_nc.data}")

            if not check_nc.data:
                self.show_error("Erro: NC não encontrada no banco (ID inexistente na View).")
                return
            
            status = check_nc.data[0].get('status_calculado')
            if status != 'Ativa':
                self.show_error(f"Erro: Esta cota de NC está com status: {status}")
                return

            # 3. Conversão de valor
            try:
                valor_float = float(self.modal_txt_valor_empenhado.value.replace(".", "").replace(",", "."))
            except ValueError:
                self.show_error("Valor de empenho inválido.")
                return

            # 4. Montagem dos dados para o Supabase
            dados_ne = {
                "numero_ne": self.modal_txt_numero_ne.value.strip(),
                "valor_empenhado": valor_float,
                "id_distribuicao": self.modal_txt_nc.value, # FK para a tabela de distribuição
                "data_empenho": self.modal_txt_data_empenho.value,
                "descricao": self.modal_txt_descricao.value
            }

            # 5. Salvamento
            if self.id_sendo_editado:
                supabase.table('notas_de_empenho').update(dados_ne).eq('id', self.id_sendo_editado).execute()
            else:
                supabase.table('notas_de_empenho').insert(dados_ne).execute()

            self.show_success_snackbar("Nota de Empenho salva com sucesso!")
            self.close_modal(None)
            self.load_nes_data()
            
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None)

        except Exception as ex:
            print(f"Erro Crítico no save_ne: {ex}")
            self.handle_db_error(ex, "salvar NE")
            
    def open_confirm_delete(self, ne):
        print(f"A pedir confirmação para excluir NE: {ne['numero_ne']}")
        self.confirm_delete_dialog.data = ne['id'] 
        self.page.dialog = self.confirm_delete_dialog 
        self.confirm_delete_dialog.open = True
        self.page.update()

    def close_confirm_delete(self, e):
        self.confirm_delete_dialog.open = False
        self.page.update()

    def confirm_delete(self, e):
        id_para_excluir = self.confirm_delete_dialog.data
        if not id_para_excluir:
            self.show_error("Erro: ID da NE para exclusão não encontrado.")
            self.close_confirm_delete(None)
            return

        try:
            print(f"A excluir NE ID: {id_para_excluir}...")
            supabase.table('notas_de_empenho').delete().eq('id', id_para_excluir).execute()
            print("NE excluída com sucesso.")
            
            self.show_success_snackbar("Nota de Empenho excluída com sucesso.")
            
            self.close_confirm_delete(None)
            self.load_nes_data() 
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None) 
                
        except Exception as ex:
            print(f"Erro ao excluir NE: {ex}")
            self.handle_db_error(ex, "excluir NE")
            self.close_confirm_delete(None)

def create_nes_view(page: ft.Page, on_data_changed=None, error_modal=None): 
    """
    Exporta a nossa NesView como um controlo Flet padrão.
    """
    return NesView(page, on_data_changed=on_data_changed, error_modal=error_modal)
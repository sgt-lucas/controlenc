# views/dashboard_view.py
# (Versão Refatorada v1.2 - Layout Moderno)
# (Organiza a UI em Cards)

import flet as ft
import traceback 
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime, timedelta

class DashboardView(ft.Column):
    """
    Representa o conteúdo da aba Dashboard.
    (v1.2) Refatorado para usar Cards.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.error_modal = error_modal
        
        # 1. COMPONENTES DE DADOS (KPIs)
        # Definidos primeiro para evitar NameError
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        self.txt_total_alocado = ft.Text("R$ 0,00", size=18, weight=ft.FontWeight.W_500)
        self.txt_total_empenhado = ft.Text("R$ 0,00", size=18, weight=ft.FontWeight.W_500)
        self.txt_saldo_total = ft.Text("R$ 0,00", size=32, weight=ft.FontWeight.BOLD)
        
        # 2. TABELA (Já com as 7 colunas conforme sua versão)
        self.tabela_vencendo = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Número NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Seção", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Prazo Empenho", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Inicial", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Saldo Disponível", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[], 
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        # 3. CONTROLOS DE FILTRO
        self.filtro_pi = ft.Dropdown(
            label="Filtrar Saldo por PI",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True,
            on_change=self.on_pi_filter_change
        )
        self.filtro_nd = ft.Dropdown(
            label="Filtrar Saldo por ND",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True,
            on_change=self.load_dashboard_data_wrapper 
        )
        # NOVIDADE: Adição do filtro de Seção seguindo sua lógica
        self.filtro_secao = ft.Dropdown(
            label="Filtrar Saldo por Seção",
            options=[ft.dropdown.Option(text="Todas as Seções", key="Todas")],
            expand=True,
            on_change=self.load_dashboard_data_wrapper 
        )
        self.filtro_status = ft.Dropdown(
            label="Filtrar Saldo por Status",
            options=[
                ft.dropdown.Option(text="Ativa", key="Ativa"), 
                ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"),
                ft.dropdown.Option(text="Vencida", key="Vencida"),
                ft.dropdown.Option(text="Cancelada", key="Cancelada"),
            ],
            value="Ativa",
            expand=True,
            on_change=self.load_dashboard_data_wrapper
        )
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros do Saldo",
            on_click=self.limpar_filtros
        )

        # --- (A) Variáveis de Estado ---
        self.graficos_expandidos = False  
        self.tabela_expandida = True      

        # --- (B) Definição do Gráfico (Versão Segura) ---
        self.grafico_saldos = ft.BarChart(
            bar_groups=[],
            border=ft.border.all(1, "grey300"),
            left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Saldo (R$)")), # Removido with_labels
            bottom_axis=ft.ChartAxis(labels_size=32), # Removido with_labels
            expand=True,
            interactive=True,
        )

        # Contentor do gráfico (começa invisível)
        self.coluna_conteudo_grafico = ft.Column(
            [
                ft.Divider(),
                ft.Container(content=self.grafico_saldos, height=300, padding=10)
            ],
            visible=self.graficos_expandidos
        )

        # Contentor da tabela (começa visível)
        self.coluna_conteudo_tabela = ft.Column(
            [
                ft.Divider(), 
                ft.Container(content=self.tabela_vencendo, expand=True)
            ],
            visible=self.tabela_expandida
        )

        # 4. MONTAGEM DO CARD DE SALDO E FILTROS (Refatorado v1.2.1)
        card_saldo_e_filtros = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        # Título e Refresh
                        ft.Row(
                            [
                                ft.Text("Painel de Saldos Consolidados", size=20, weight="w600"),
                                ft.Row([
                                    self.btn_limpar_filtros,
                                    ft.IconButton(
                                        icon="REFRESH", 
                                        on_click=self.load_dashboard_data_wrapper, 
                                        tooltip="Recarregar e Aplicar Filtros"
                                    ),
                                    self.progress_ring,
                                ])
                            ],
                            alignment="spaceBetween"
                        ),
                        
                        # Mostradores KPI (Total Alocado | Total Empenhado | Saldo)
                        ft.ResponsiveRow([
                            ft.Column(col={"sm": 4}, controls=[ft.Text("Total Recebido", size=12), self.txt_total_alocado]),
                            ft.Column(col={"sm": 4}, controls=[ft.Text("Total Empenhado", size=12), self.txt_total_empenhado]),
                            ft.Column(col={"sm": 4}, controls=[ft.Text("Saldo Disponível", size=12, weight="bold"), self.txt_saldo_total]),
                        ]),

                        ft.Divider(),

                        # Linhas de Filtros
                        ft.Text("Filtros Aplicados:", weight="bold"),
                        ft.ResponsiveRow(
                            [
                                ft.Column(col={"sm": 12, "md": 4}, controls=[self.filtro_pi]),
                                ft.Column(col={"sm": 12, "md": 4}, controls=[self.filtro_nd]),
                            ]
                        ),
                        ft.ResponsiveRow(
                            [
                                ft.Column(col={"sm": 12, "md": 4}, controls=[self.filtro_status]),
                                ft.Column(col={"sm": 12, "md": 4}, controls=[self.filtro_secao]),
                            ],
                        )
                    ],
                    spacing=15
                )
            )
        )

        # --- Card 2: Análise Gráfica (Novo) ---
        card_graficos = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Text("Distribuição de Saldo por Seção", size=20, weight="w600"),
                        ft.IconButton(icon="ADD", on_click=self.toggle_graficos)
                    ], alignment="spaceBetween"),
                    self.coluna_conteudo_grafico
                ])
            )
        )

        # --- Card 3: Tabela "A Vencer" (Ajustado para Maximizar) ---
        # Primeiro, criamos o container que esconde
        self.coluna_conteudo_tabela = ft.Column(
            [ft.Divider(), ft.Container(content=self.tabela_vencendo, expand=True)],
            visible=self.tabela_expandida
        )

        card_tabela_vencer = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Text("Notas de Crédito a Vencer (Próximos 7 dias)", size=20, weight="w600"),
                        ft.IconButton(icon="REMOVE", on_click=self.toggle_tabela)
                    ], alignment="spaceBetween"),
                    self.coluna_conteudo_tabela
                ])
            )
        )

        # Atualize seu self.controls
        self.controls = [
            card_saldo_e_filtros, # O card que você já tem
            card_graficos,
            card_tabela_vencer,
        ]

        self.on_mount = self.on_view_mount
        
    def toggle_graficos(self, e):
        self.graficos_expandidos = not self.graficos_expandidos
        e.control.icon = "REMOVE" if self.graficos_expandidos else "ADD"
        self.coluna_conteudo_grafico.visible = self.graficos_expandidos
        self.update()

    def toggle_tabela(self, e):
        self.tabela_expandida = not self.tabela_expandida
        e.control.icon = "REMOVE" if self.tabela_expandida else "ADD"
        # Precisamos envolver o conteúdo da tabela numa coluna para esconder
        self.coluna_conteudo_tabela.visible = self.tabela_expandida
        self.update()

    def limpar_filtros(self, e):
        """Reseta todos os dropdowns e recarrega a dashboard."""
        print("Dashboard: A limpar filtros...")
        
        # Resetamos para os valores padrão que disparam o "Todos" no load_dashboard_data
        self.filtro_pi.value = "Todos os PIs"
        self.filtro_nd.value = "Todas as NDs"
        self.filtro_secao.value = "Todas" 
        self.filtro_status.value = "Ativa" # Ou "Todas", conforme sua preferência inicial
        
        # Chama o carregamento para aplicar o reset
        self.load_dashboard_data_wrapper(None)    

    def carregar_filtros_secao(self):
        """Preenche o dropdown de seções do dashboard."""
        print("Dashboard: A carregar seções no filtro...")
        # Reinicia as opções com o padrão "Todas"
        self.filtro_secao.options = [ft.dropdown.Option(text="Todas as Seções", key="Todas")]
        
        # Busca o cache que foi salvo no login
        secoes_cache = self.page.session.get("secoes_cache") or {}
        
        if secoes_cache:
            for sid, nome in secoes_cache.items():
                self.filtro_secao.options.append(ft.dropdown.Option(key=sid, text=nome))
        
        self.filtro_secao.update()

    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("DashboardView: Controlo montado. A carregar dados...")
        self.load_filter_options()
        self.carregar_filtros_secao()
        self.load_dashboard_data(None)
        
    def show_error(self, message):
        """Exibe o modal de erro global."""
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Traduz erros comuns do Supabase/PostgREST para mensagens amigáveis."""
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") 
        
        if "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def formatar_moeda(self, valor):
        """Formata um float ou string para R$ 0.000,00"""
        try:
            val = float(valor)
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"

    def load_filter_options(self, pi_selecionado=None):
        """
        Preenche os dropdowns de filtro PI e ND.
        """
        try:
            if pi_selecionado is None:
                print("Dashboard: A carregar opções de filtro (PIs e NDs)...")
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
                print("Dashboard: Opções de filtro iniciais carregadas.")
            
            else:
                print(f"Dashboard: A carregar NDs para o PI: {pi_selecionado}...")
                self.filtro_nd.disabled = True
                self.filtro_nd.update()
                nds = supabase.rpc('get_distinct_nds_for_pi', {'p_pi': pi_selecionado}).execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                         if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("Dashboard: Filtro ND atualizado.")
            
            self.filtro_nd.disabled = False
            
            if pi_selecionado is None:
                self.update() 

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO DASHBOARD [load_filter_options] ---")
            traceback.print_exc()
            print("------------------------------------------------------------------")
            
            print(f"Erro ao carregar opções de filtro no Dashboard: {ex}")
            self.handle_db_error(ex, "carregar filtros do Dashboard")

    def on_pi_filter_change(self, e):
        """
        Recarrega as opções de ND e depois recarrega os dados do Dashboard.
        """
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None
        self.load_filter_options(pi_selecionado=pi_val)
        self.load_dashboard_data(None) 

    def load_dashboard_data_wrapper(self, e):
        """Função "wrapper" para o botão recarregar."""
        self.load_dashboard_data(e)

    def load_dashboard_data(self, e):
        """
        Busca os dados no Supabase e atualiza os controlos da UI.
        Aplica filtros APENAS ao cálculo do saldo total.
        """
        print("Dashboard: A carregar dados com filtros...")
        self.progress_ring.visible = True
        self.page.update()

        try:
            # --- 1. Buscar Dados Consolidados (COM FILTROS INTELIGENTES) ---
            # Buscamos '*' para ter acesso a valor_inicial e total_empenhado também
            query = supabase.table('ncs_com_saldos').select('*')
            
            # CORREÇÃO DO BUG: Só aplica o filtro se não for a opção de "Todos"
            #if self.filtro_status.value and "Todas" not in self.filtro_status.value:
             #   query = query.eq('status_calculado', self.filtro_status.value)
            
            if self.filtro_pi.value and "Todos" not in self.filtro_pi.value:
                query = query.eq('pi', self.filtro_pi.value)
                
            if self.filtro_nd.value and "Todas" not in self.filtro_nd.value:
                query = query.eq('natureza_despesa', self.filtro_nd.value)

            # NOVO FILTRO: Seção (Certifique-se de criar o self.filtro_secao no __init__)
            if hasattr(self, 'filtro_secao') and self.filtro_secao.value and "Todas" not in self.filtro_secao.value:
                query = query.eq('id_secao', self.filtro_secao.value)

            resposta = query.execute()
            
            # --- CÁLCULO DOS KPIs (Histórico vs Disponibilidade) ---
            
            # 1. KPIs Históricos: Somam tudo o que o banco trouxe (ignora status)
            total_recebido = sum(float(item['valor_inicial']) for item in resposta.data) if resposta.data else 0.0
            total_empenhado = sum(float(item['total_empenhado']) for item in resposta.data) if resposta.data else 0.0
            
            # 2. Filtragem Local: Filtramos os dados em Python para o Saldo e o Gráfico
            status_alvo = self.filtro_status.value
            if status_alvo and "Todas" not in status_alvo:
                # Cria uma lista apenas com as NCs que batem com o status (ex: "Ativa")
                dados_filtrados = [d for d in resposta.data if d['status_calculado'] == status_alvo]
            else:
                dados_filtrados = resposta.data or []

            # 3. Saldo Total: Baseado apenas nos dados filtrados pelo status
            saldo_total = sum(float(item['saldo_disponivel']) for item in dados_filtrados)
            
            # Atualiza os componentes da tela
            self.txt_total_alocado.value = self.formatar_moeda(total_recebido)
            self.txt_total_empenhado.value = self.formatar_moeda(total_empenhado)
            self.txt_saldo_total.value = self.formatar_moeda(saldo_total)

            # --- ATUALIZAÇÃO DO GRÁFICO ---
            saldos_por_secao = {}
            if resposta.data:
                for item in dados_filtrados:
                    nome = item.get('nome_secao', 'N/A')
                    valor = float(item['saldo_disponivel'])
                    saldos_por_secao[nome] = saldos_por_secao.get(nome, 0) + valor

            novas_barras = []
            labels_eixo_x = [] # Lista para guardar os nomes das seções
            max_y_encontrado = 100
            
            for i, (nome, valor) in enumerate(saldos_por_secao.items()):
                if valor > max_y_encontrado: max_y_encontrado = valor
                
                # Criar a barra
                novas_barras.append(
                    ft.BarChartGroup(
                        x=i,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0, to_y=valor, width=30, 
                                color="blue", border_radius=5,
                                tooltip=f"{nome}: {self.formatar_moeda(valor)}"
                            )
                        ]
                    )
                )
                
                # Criar a legenda para esta barra específica
                labels_eixo_x.append(
                    ft.ChartAxisLabel(
                        value=i,
                        label=ft.Container(ft.Text(nome, size=10, weight="bold"), padding=ft.padding.only(top=10))
                    )
                )
            
            # Aplicar ao gráfico
            self.grafico_saldos.bar_groups = novas_barras
            self.grafico_saldos.bottom_axis.labels = labels_eixo_x # Define as legendas fixas
            self.grafico_saldos.max_y = max_y_encontrado * 1.15
            
            # --- 2. Buscar NCs a Vencer (Próximos 7 dias) ---
            hoje = datetime.now().date()
            em_7_dias = hoje + timedelta(days=7)
            
            # Note que adicionamos 'nome_secao' à busca para a tabela não ficar crua
            resposta_vencendo = supabase.table('ncs_com_saldos') \
                .select('numero_nc, nome_secao, data_validade_empenho, saldo_disponivel, pi, natureza_despesa, valor_inicial') \
                .filter('status_calculado', 'eq', 'Ativa') \
                .filter('data_validade_empenho', 'gte', hoje.isoformat()) \
                .filter('data_validade_empenho', 'lte', em_7_dias.isoformat()) \
                .order('data_validade_empenho', desc=False) \
                .execute()

            # --- 3. Preencher a Tabela com a Coluna SEÇÃO ---
            self.tabela_vencendo.rows.clear()
            if resposta_vencendo.data:
                for nc in resposta_vencendo.data:
                    data_formatada = datetime.fromisoformat(nc['data_validade_empenho']).strftime('%d/%m/%Y')
                    self.tabela_vencendo.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(nc['numero_nc'])),
                                ft.DataCell(ft.Text(nc.get('nome_secao', 'N/A'))), # Melhora: Mostra a seção
                                ft.DataCell(ft.Text(data_formatada)),
                                ft.DataCell(ft.Text(nc['pi'])),
                                ft.DataCell(ft.Text(nc['natureza_despesa'])),
                                ft.DataCell(ft.Text(self.formatar_moeda(nc['valor_inicial']))),
                                ft.DataCell(ft.Text(self.formatar_moeda(nc['saldo_disponivel']))),
                            ]
                        )
                    )
            else:
                # Caso não haja dados, exibe mensagem amigável (ajustado para 7 colunas)
                self.tabela_vencendo.rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text("Sem NCs críticas nos próximos 7 dias.", italic=True)),
                            ft.DataCell(ft.Text("")), # Coluna Seção
                            ft.DataCell(ft.Text("")), # Coluna Prazo
                            ft.DataCell(ft.Text("")), # Coluna PI
                            ft.DataCell(ft.Text("")), # Coluna ND
                            ft.DataCell(ft.Text("")), # Coluna Valor Inicial
                            ft.DataCell(ft.Text("")), # Coluna Saldo
                        ]
                    )
                )

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO DASHBOARD [load_dashboard_data] ---")
            traceback.print_exc() 
            print("-------------------------------------------------------------------")
            
            print(f"Erro ao carregar dashboard: {ex}")
            self.handle_db_error(ex, "carregar dados do Dashboard")
        
        finally:
            self.progress_ring.visible = False
            self.page.update()
        
    def limpar_filtros(self, e):
        """
        Limpa os filtros do saldo e recarrega os dados.
        """
        print("Dashboard: A limpar filtros do saldo...")
        self.filtro_pi.value = None
        self.filtro_nd.value = None
        self.filtro_status.value = "Ativa" # Volta ao default
        
        self.load_filter_options(pi_selecionado=None) 
        self.load_dashboard_data(None)
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_dashboard_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa DashboardView como um controlo Flet padrão.
    """
    return DashboardView(page, error_modal=error_modal)
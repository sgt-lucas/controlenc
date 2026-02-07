# views/dashboard_view.py
# (Versão Definitiva - Conectada à View ncs_com_saldos)

import flet as ft
import traceback 
from datetime import datetime, timedelta
import database

class DashboardView(ft.Column):
    """
    Representa o conteúdo da aba Dashboard.
    Refatorado para calcular KPIs baseados na consistência matemática:
    Utilizado = Alocado - Saldo.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.error_modal = error_modal
        
        # 1. COMPONENTES DE DADOS (KPIs)
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        # KPIs com cores para facilitar leitura
        self.txt_total_alocado = ft.Text("R$ 0,00", size=18, weight=ft.FontWeight.W_500, color=ft.colors.BLUE_GREY)
        self.txt_total_utilizado = ft.Text("R$ 0,00", size=18, weight=ft.FontWeight.W_500, color=ft.colors.ORANGE_800)
        self.txt_saldo_total = ft.Text("R$ 0,00", size=32, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_800)
        
        # 2. TABELA "A VENCER"
        self.tabela_vencendo = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Seção", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Prazo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Inicial", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Saldo", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[], 
            border=ft.border.all(1, "grey200"),
            border_radius=8,
            heading_row_color=ft.colors.BLUE_50,
        )
        
        # 3. CONTROLOS DE FILTRO
        self.filtro_pi = ft.Dropdown(
            label="Filtrar por PI",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            ##expand=true,
            on_change=self.on_pi_filter_change,
            dense=True
        )
        self.filtro_nd = ft.Dropdown(
            label="Filtrar por ND",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            #expand=true,
            on_change=self.load_dashboard_data_wrapper,
            dense=True
        )
        self.filtro_secao = ft.Dropdown(
            label="Filtrar por Seção",
            options=[ft.dropdown.Option(text="Todas as Seções", key="Todas")],
            #expand=true,
            on_change=self.load_dashboard_data_wrapper,
            dense=True
        )
        self.filtro_status = ft.Dropdown(
            label="Status",
            options=[
                ft.dropdown.Option(text="Ativa", key="Ativa"), 
                ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"),
                ft.dropdown.Option(text="Vencida", key="Vencida"),
                ft.dropdown.Option(text="Cancelada", key="Cancelada"),
            ],
            value="Ativa",
            #expand=true,
            on_change=self.load_dashboard_data_wrapper,
            dense=True
        )
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros",
            on_click=self.limpar_filtros
        )

        # --- Variáveis de Estado UI ---
        self.graficos_expandidos = True # Gráfico visível por padrão fica bonito
        self.tabela_expandida = True      

        # --- Gráfico de Barras ---
        self.grafico_saldos = ft.BarChart(
            bar_groups=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Saldo (R$)", size=10)),
            bottom_axis=ft.ChartAxis(labels_size=32),
            interactive=True,
            animate=True,
        )

        self.coluna_conteudo_grafico = ft.Column(
            [
                ft.Divider(),
                ft.Container(content=self.grafico_saldos, height=300, padding=10)
            ],
            visible=self.graficos_expandidos
        )

        self.coluna_conteudo_tabela = ft.Column(
            [
                ft.Divider(), 
                ft.Container(content=self.tabela_vencendo)
            ],
            visible=self.tabela_expandida
        )

        # 4. LAYOUT DOS CARDS
        
        # Card 1: Painel de Controle (KPIs + Filtros)
        card_painel = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Painel de Saldos Consolidados", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    self.btn_limpar_filtros,
                                    ft.IconButton(icon="REFRESH", on_click=self.load_dashboard_data_wrapper, tooltip="Atualizar"),
                                    self.progress_ring,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        
                        # KPIs
                        ft.Container(
                            padding=10,
                            border=ft.border.all(1, ft.colors.GREY_200),
                            border_radius=10,
                            content=ft.ResponsiveRow([
                                ft.Column(col={"sm": 4}, controls=[ft.Text("Total Recebido", size=12, color="grey"), self.txt_total_alocado]),
                                ft.Column(col={"sm": 4}, controls=[ft.Text("Total Utilizado", size=12, color="grey"), self.txt_total_utilizado]),
                                ft.Column(col={"sm": 4}, controls=[ft.Text("Saldo Disponível", size=12, weight="bold", color="grey"), self.txt_saldo_total]),
                            ])
                        ),

                        # Filtros
                        ft.Text("Filtros Aplicados:", weight=ft.FontWeight.BOLD, size=12),
                        ft.ResponsiveRow(
                            [
                                ft.Column(col={"sm": 12, "md": 3}, controls=[self.filtro_secao]),
                                ft.Column(col={"sm": 12, "md": 3}, controls=[self.filtro_pi]),
                                ft.Column(col={"sm": 12, "md": 3}, controls=[self.filtro_nd]),
                                ft.Column(col={"sm": 12, "md": 3}, controls=[self.filtro_status]),
                            ],
                        )
                    ],
                    spacing=15
                )
            )
        )

        # Card 2: Gráfico
        card_graficos = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Text("Distribuição de Saldo por Seção", size=18, weight=ft.FontWeight.W_600),
                        ft.IconButton(icon="REMOVE" if self.graficos_expandidos else "ADD", on_click=self.toggle_graficos)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.coluna_conteudo_grafico
                ])
            )
        )

        # Card 3: Tabela
        card_tabela = ft.Card(
            elevation=2,
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Text("Atenção: Créditos vencendo em 7 dias", size=18, weight=ft.FontWeight.W_600, color=ft.colors.RED_700),
                        ft.IconButton(icon="REMOVE" if self.tabela_expandida else "ADD", on_click=self.toggle_tabela)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.coluna_conteudo_tabela
                ])
            )
        )

        self.controls = [card_painel, card_graficos, card_tabela]
        self.progress_ring.visible = False
        self.on_mount = self.on_view_mount
        
    def toggle_graficos(self, e):
        self.graficos_expandidos = not self.graficos_expandidos
        e.control.icon = "REMOVE" if self.graficos_expandidos else "ADD"
        self.coluna_conteudo_grafico.visible = self.graficos_expandidos
        self.update()

    def toggle_tabela(self, e):
        self.tabela_expandida = not self.tabela_expandida
        e.control.icon = "REMOVE" if self.tabela_expandida else "ADD"
        self.coluna_conteudo_tabela.visible = self.tabela_expandida
        self.update()

    def formatar_moeda(self, valor):
        try:
            val = float(valor)
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "R$ 0,00"

    def on_view_mount(self, e):
        """Ao montar, carrega filtros e dados."""
        self.carregar_filtros_secao()
        self.load_filter_options()
        self.load_dashboard_data(None)
        
    def carregar_filtros_secao(self):
        """Carrega seções do cache (definido no main)."""
        try:
            self.filtro_secao.options = [ft.dropdown.Option(text="Todas as Seções", key="Todas")]
            secoes_cache = self.page.session.get("cache_secoes_map") or {}
            for sid, nome in secoes_cache.items():
                self.filtro_secao.options.append(ft.dropdown.Option(key=str(sid), text=nome))
            self.filtro_secao.update()
        except: pass

    def load_filter_options(self, pi_selecionado=None):
        """Carrega PIs e NDs do banco."""
        try:
            if pi_selecionado is None:
                pis = database.execute_query("SELECT DISTINCT pi FROM ncs_com_saldos ORDER BY pi")
                self.filtro_pi.options = [ft.dropdown.Option(text="Todos os PIs", key=None)]
                for row in pis:
                    if row['pi']: self.filtro_pi.options.append(ft.dropdown.Option(text=row['pi'], key=row['pi']))
                
                nds = database.execute_query("SELECT DISTINCT natureza_despesa FROM ncs_com_saldos ORDER BY natureza_despesa")
                self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key=None)]
                for row in nds:
                    if row['natureza_despesa']: self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
            else:
                nds = database.execute_query("SELECT DISTINCT natureza_despesa FROM ncs_com_saldos WHERE pi = %s ORDER BY natureza_despesa", (pi_selecionado,))
                self.filtro_nd.options = [ft.dropdown.Option(text="Todas as NDs", key=None)]
                for row in nds:
                    self.filtro_nd.options.append(ft.dropdown.Option(text=row['natureza_despesa'], key=row['natureza_despesa']))
            if self.page: self.update()
        except Exception as ex:
            print(f"Erro filtros dashboard: {ex}")

    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value and "Todos" not in self.filtro_pi.value else None
        self.filtro_nd.value = None
        self.load_filter_options(pi_selecionado=pi_val)
        self.load_dashboard_data(None) 

    def load_dashboard_data_wrapper(self, e):
        self.load_dashboard_data(e)

    def load_dashboard_data(self, e):
        """Lógica Principal: Carrega dados, calcula KPIs e atualiza Gráficos."""
        self.progress_ring.visible = True
        if self.page: self.page.update()

        try:
            # 1. Busca Dados na View
            sql = "SELECT * FROM ncs_com_saldos WHERE 1=1"
            params = []

            if self.filtro_pi.value and "Todos" not in self.filtro_pi.value:
                sql += " AND pi = %s"; params.append(self.filtro_pi.value)
            if self.filtro_nd.value and "Todas" not in self.filtro_nd.value:
                sql += " AND natureza_despesa = %s"; params.append(self.filtro_nd.value)
            if self.filtro_secao.value and "Todas" not in self.filtro_secao.value:
                sql += " AND id_secao = %s"; params.append(int(self.filtro_secao.value))

            dados_brutos = database.execute_query(sql, tuple(params))
            
            # 2. Cálculos Matemáticos (KPIS)
            # Total Alocado = Soma de valor_inicial
            total_alocado = sum(float(item['valor_inicial'] or 0) for item in dados_brutos) if dados_brutos else 0.0
            
            # Filtragem de Status para o Saldo e Utilizado
            status_alvo = self.filtro_status.value
            dados_filtrados = [d for d in dados_brutos if d['status_calculado'] == status_alvo] if status_alvo and "Todas" not in status_alvo else (dados_brutos or [])
            
            # Saldo Total = Soma de saldo_disponivel
            saldo_total = sum(float(item['saldo_disponivel'] or 0) for item in dados_filtrados)
            
            # Total Utilizado (Empenhado + Recolhido) = Alocado - Saldo
            # Nota: Usamos os dados filtrados para consistência visual se o usuário filtrar por status.
            # Se ele ver "Ativas", ele verá Alocado das Ativas - Saldo das Ativas = Utilizado das Ativas.
            total_alocado_filtrado = sum(float(item['valor_inicial'] or 0) for item in dados_filtrados)
            total_utilizado = total_alocado_filtrado - saldo_total
            
            self.txt_total_alocado.value = self.formatar_moeda(total_alocado_filtrado)
            self.txt_total_utilizado.value = self.formatar_moeda(total_utilizado)
            self.txt_saldo_total.value = self.formatar_moeda(saldo_total)

            # 3. Atualização do Gráfico (Saldos por Seção)
            saldos_por_secao = {}
            for item in dados_filtrados:
                nome = item.get('nome_secao', 'N/A')
                valor = float(item.get('saldo_disponivel', 0))
                if valor > 0: # Só mostra seções com saldo no gráfico
                    saldos_por_secao[nome] = saldos_por_secao.get(nome, 0) + valor

            novas_barras = []
            labels_eixo_x = []
            max_y = 100
            
            # Ordena por valor decrescente
            secoes_sorted = sorted(saldos_por_secao.items(), key=lambda x: x[1], reverse=True)
            
            for i, (nome, valor) in enumerate(secoes_sorted):
                if valor > max_y: max_y = valor
                # Barra Azul
                novas_barras.append(ft.BarChartGroup(x=i, bar_rods=[
                    ft.BarChartRod(from_y=0, to_y=valor, width=30, color=ft.colors.BLUE_700, border_radius=4, 
                                   tooltip=f"{nome}: {self.formatar_moeda(valor)}")
                ]))
                # Rótulo Rotacionado
                labels_eixo_x.append(ft.ChartAxisLabel(value=i, label=ft.Text(nome[:10], size=10, weight="bold", rotate=45)))

            self.grafico_saldos.bar_groups = novas_barras
            self.grafico_saldos.bottom_axis.labels = labels_eixo_x
            self.grafico_saldos.max_y = max_y * 1.15 # Margem superior
            
            # 4. Tabela de Vencimentos (Próximos 7 dias)
            hoje = datetime.now().date()
            em_7_dias = hoje + timedelta(days=7)
            
            # Filtra na memória para aproveitar a query já feita e evitar ir ao banco de novo
            dados_vencendo = [
                d for d in dados_brutos 
                if d['status_calculado'] == 'Ativa' 
                and d.get('data_validade_empenho') 
                and hoje <= (d['data_validade_empenho'] if isinstance(d['data_validade_empenho'], datetime) else datetime.fromisoformat(str(d['data_validade_empenho'])).date()) <= em_7_dias
            ]

            self.tabela_vencendo.rows.clear()
            if dados_vencendo:
                for nc in dados_vencendo:
                    d_raw = nc.get('data_validade_empenho')
                    if hasattr(d_raw, 'strftime'): data_fmt = d_raw.strftime('%d/%m/%Y')
                    else: data_fmt = datetime.fromisoformat(str(d_raw)).strftime('%d/%m/%Y')
                    
                    self.tabela_vencendo.rows.append(ft.DataRow(cells=[
                        ft.DataCell(ft.Text(nc.get('numero_nc', '-'))), 
                        ft.DataCell(ft.Text(nc.get('nome_secao', '-'))),
                        ft.DataCell(ft.Text(data_fmt)), 
                        ft.DataCell(ft.Text(nc.get('pi', '-'))),
                        ft.DataCell(ft.Text(nc.get('natureza_despesa', '-'))),
                        ft.DataCell(ft.Text(self.formatar_moeda(nc.get('valor_inicial', 0)))),
                        ft.DataCell(ft.Text(self.formatar_moeda(nc.get('saldo_disponivel', 0))))
                    ]))
            else:
                self.tabela_vencendo.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("Nenhuma cota vencendo em breve.", italic=True)), *[ft.DataCell(ft.Text(""))]*6]))

        except Exception as ex:
            traceback.print_exc()
            self.handle_db_error(ex, "carregar dados do Dashboard")
        finally:
            self.progress_ring.visible = False
            if self.page: self.page.update()

    def limpar_filtros(self, e):
        """Limpa filtros e recarrega."""
        self.filtro_pi.value = None
        self.filtro_nd.value = None
        self.filtro_secao.value = "Todas"
        self.filtro_status.value = "Ativa"
        self.load_filter_options(None)
        self.load_dashboard_data(None)

def create_dashboard_view(page: ft.Page, error_modal=None):
    return DashboardView(page, error_modal=error_modal)
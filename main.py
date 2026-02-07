# main.py
# (Versão Nacionalizada v3.0 - Banco Local PostgreSQL 17)

import flet as ft
import os 
import traceback 
import hashlib
import database # Seu arquivo database.py local

# Define a chave secreta para a sessão local
os.environ["FLET_SECRET_KEY"] = os.environ.get("FLET_SECRET_KEY", "chave_secreta_local_padrao_12345!")

# Importação das Views
from views.dashboard_view import create_dashboard_view
from views.ncs_view import create_ncs_view
from views.nes_view import create_nes_view
from views.relatorios_view import create_relatorios_view
from views.admin_view import create_admin_view

class ErrorModal:
    def __init__(self, page: ft.Page):
        self.page = page
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(name="ERROR_OUTLINE", color="red"), 
                ft.Text("Ocorreu um Erro")
            ]),
            content=ft.Text("Mensagem de erro padrão."),
            actions=[ft.TextButton("OK", on_click=self.close)],
            actions_alignment=ft.MainAxisAlignment.END
        )
        if self.dialog not in self.page.overlay:
             self.page.overlay.append(self.dialog)

    def show(self, error_message):
        print(f"[Modal de Erro] {error_message}")
        self.dialog.content = ft.Text(str(error_message))
        self.dialog.open = True
        self.page.update()

    def close(self, e=None):
        self.dialog.open = False
        self.page.update()

def create_sidebar_item(icon, label, selected=False, on_click=None):
    """Cria um item de menu com design moderno e seguro contra erros de sintaxe."""
    color = "#2D3924" if selected else "grey600"
    bg_color = "#E8EBE8" if selected else "transparent"
    
    # Criamos o container sem o argumento problemático 'mouse_cursor'
    item = ft.Container(
        content=ft.Row(
            [
                ft.VerticalDivider(width=4, thickness=4, color="#2D3924" if selected else "transparent"),
                ft.Icon(icon, color=color, size=22),
                ft.Text(label, color=color, size=14, weight=ft.FontWeight.W_500 if selected else ft.FontWeight.NORMAL),
            ],
            spacing=15,
        ),
        height=50,
        bgcolor=bg_color,
        border_radius=ft.border_radius.only(top_right=25, bottom_right=25),
        on_click=on_click,
    )
    
    # Tentamos definir o cursor separadamente (mais seguro)
    try:
        item.mouse_cursor = ft.MouseCursor.CLICK
    except:
        pass # Se falhar, o sistema continua funcionando sem o cursor de mãozinha

    # Lógica de Hover (Passar o mouse) isolada para evitar erros de renderização
    def handle_hover(e):
        if not selected:
            e.control.bgcolor = "#F0F2F0" if e.data == "true" else bg_color
            e.control.update()
            
    item.on_hover = handle_hover
    return item

def _load_global_caches(page: ft.Page):
    """Busca dados de filtro comuns no PostgreSQL local e armazena na sessão."""
    print("A carregar caches globais do banco local...")
    try:
        # 1. Buscar PIs (Usando consulta SQL local)
        pis_data = database.execute_query("SELECT DISTINCT pi FROM notas_de_credito ORDER BY pi")
        page.session.set("cache_pis", [p['pi'] for p in pis_data] if pis_data else [])

        # 2. Buscar NDs
        nds_data = database.execute_query("SELECT DISTINCT natureza_despesa FROM notas_de_credito ORDER BY natureza_despesa")
        page.session.set("cache_nds", [n['natureza_despesa'] for n in nds_data] if nds_data else [])

        # 3. Buscar Seções
        secoes_resp = database.execute_query("SELECT id, nome FROM secoes")
        secoes_map = {s['id']: s['nome'] for s in secoes_resp} if secoes_resp else {}
        page.session.set("cache_secoes_map", secoes_map)

        # 4. Buscar Lista de NCs
        ncs_resp = database.execute_query("SELECT id, numero_nc FROM notas_de_credito ORDER BY numero_nc")
        page.session.set("cache_ncs_lista", ncs_resp or [])
        
        return True
    except Exception as e:
        print(f"ERRO AO CARREGAR CACHES LOCAIS: {e}")
        return e 

def main(page: ft.Page):
    page.title = "SISTEMA DE CONTROLE DE NOTAS DE CRÉDITO - SALC" 
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#2D3924",       # Verde Oliva Escuro
            secondary="#C5A059",     # Dourado para detalhes
            on_primary="white",
            background="#F4F4F4",    # Cinza muito claro (fundo do site EB)
            surface="white",
        )
    )
    error_modal_global = ErrorModal(page)

    # DEFINIÇÃO DOS CAMPOS (Fora de funções para evitar NameError)
    username_field = ft.TextField(label="Utilizador", prefix_icon="PERSON", autofocus=True)
    password_field = ft.TextField(label="Senha", prefix_icon="LOCK", password=True, can_reveal_password=True)

    def show_main_layout(e=None):
        page.clean()
        page.bgcolor = "#F0F2F0" 
        
        user = page.session.get("user")
        if not user:
            handle_logout()
            return

        # TÉCNICO: Definimos a coluna ANTES de qualquer função ou layout que a use
        sidebar_column = ft.Column(spacing=5, tight=True)
        view_content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=20)

        def on_data_changed_master(e=None):
            print("Atualizando caches globais pós-alteração...")
            _load_global_caches(page)

        # 3. BARRA SUPERIOR (AppBar)
        page.appbar = ft.AppBar(
            leading=ft.Container(
                content=ft.Image(
                    src="https://www.eb.mil.br/image/layout_set_logo?img_id=40375&t=1768403138032", 
                    fit=ft.ImageFit.CONTAIN
                ),
                padding=8
            ),
            title=ft.Text("SALC | Controle de Notas de Crédito", weight="bold"), 
            bgcolor="#2D3924", 
            color="white",
            actions=[
                ft.Container(content=ft.Text(f"Utilizador: {user.get('nome')}"), padding=20),
                ft.IconButton(icon=ft.icons.LOGOUT, on_click=lambda _: handle_logout(), icon_color="white")
            ]
        )

        # 4. DEFINIÇÃO DAS VIEWS
        all_views = [
            {"label": "Painel", "icon": ft.icons.DASHBOARD_ROUNDED, "view": create_dashboard_view(page, error_modal=error_modal_global)},
            {"label": "NCs", "icon": ft.icons.PAYMENT_ROUNDED, "view": create_ncs_view(page, on_data_changed=on_data_changed_master, error_modal=error_modal_global)},
            {"label": "NEs", "icon": ft.icons.RECEIPT_LONG_ROUNDED, "view": create_nes_view(page, on_data_changed=on_data_changed_master, error_modal=error_modal_global)},
            {"label": "Relatórios", "icon": ft.icons.ANALYTICS_ROUNDED, "view": create_relatorios_view(page, error_modal=error_modal_global)},
        ]
        
        if user.get("is_admin"):
            all_views.append({"label": "Admin", "icon": ft.icons.ADMIN_PANEL_SETTINGS_ROUNDED, "view": create_admin_view(page, error_modal=error_modal_global)})

        # 5. LÓGICA DE NAVEGAÇÃO DA SIDEBAR
        def update_menu(index):
            sidebar_column.controls.clear()
            for i, item in enumerate(all_views):
                sidebar_column.controls.append(
                    create_sidebar_item(
                        icon=item["icon"],
                        label=item["label"],
                        selected=(i == index),
                        on_click=lambda e, idx=i: select_view(idx)
                    )
                )
            if sidebar_column.page:
                sidebar_column.update()

        def select_view(index):
            view_selecionada = all_views[index]["view"]
            view_content.controls = [view_selecionada]
            
            # TÉCNICO: Forçamos a atualização da página antes de montar os dados
            page.update() 

            if hasattr(view_selecionada, "on_view_mount"):
                # Garante que os componentes Flet já existem na tela antes de carregar o SQL
                view_selecionada.on_view_mount(None)
            
            update_menu(index)
        

        # 6. MONTAGEM FINAL DO LAYOUT (Sidebar SaaS Style)
        page.add(
            ft.Row(
                [
                    # Sidebar Larga e Profissional
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(height=20),
                                sidebar_column,
                                ft.Container(expand=True),
                                ft.Text("v2.5.0 EB-Local", size=10, color="grey400"),
                                ft.Container(height=10),
                            ],
                            horizontal_alignment="center",
                        ),
                        width=220, 
                        bgcolor="white",
                        border=ft.border.only(right=ft.border.BorderSide(1, "#D0D5D0")),
                    ),
                    # Conteúdo Principal
                    ft.Container(
                        content=view_content,
                        expand=True,
                        padding=ft.padding.only(left=40, right=40, top=30, bottom=30),
                    )
                ],
                expand=True,
                spacing=0
            )
        )
        select_view(0)
        page.update()

    def handle_login(e):
        # Captura o valor e remove espaços
        utilizador_raw = username_field.value.strip().lower()
        senha = password_field.value.strip()
        
        if not utilizador_raw or not senha:
            error_modal_global.show("Por favor, preencha todos os campos.")
            return

        # USABILIDADE: Adiciona o domínio automaticamente se não houver '@'
        email = utilizador_raw if "@" in utilizador_raw else f"{utilizador_raw}@salc.com"

        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        try:
            query = "SELECT id, email, nome, is_admin FROM usuarios WHERE email = %s AND senha_hash = %s"
            user = database.execute_query(query, (email, senha_hash))
            
            if user:
                page.session.set("user", user[0])
                page.session.set("user_email", email) # Para exibir no AppBar
                _load_global_caches(page)
                show_main_layout()
            else:
                error_modal_global.show("Utilizador ou senha incorretos.")
        except Exception as ex:
            import traceback
            traceback.print_exc()
            error_modal_global.show(f"Erro no banco local: {ex}")

    def handle_logout():
        page.session.clear()
        page.clean()
        page.add(build_login_view())
        page.update()

    def build_login_view():
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.bgcolor = "#2D3924" # Fundo sólido no tom do cabeçalho do EB

        return ft.Container(
            content=ft.Card(
                elevation=20,
                width=420,
                content=ft.Container(
                    padding=40,
                    border_radius=10,
                    bgcolor="white",
                    content=ft.Column(
                        [
                            ft.Image(
                                src="https://www.eb.mil.br/image/layout_set_logo?img_id=40375&t=1768403138032", # Brasão Oficial
                                width=80,
                                height=80,
                            ),
                            ft.Text(
                                "SALC",
                                size=22,
                                weight="bold",
                                color="#2D3924",
                                font_family="Verdana"
                            ),
                            ft.Text(
                                "Controle de Notas de Crédito",
                                size=14,
                                italic=True,
                                color="#3E4D35"
                            ),
                            ft.Divider(height=40, thickness=1, color="#E0E0E0"),
                            
                            # Campos de Entrada
                            username_field,
                            ft.Container(height=5),
                            password_field,
                            
                            ft.Container(height=25),
                            
                            # Botão Estilizado com Verde Militar
                            ft.ElevatedButton(
                                "ENTRAR",
                                on_click=handle_login,
                                width=400,
                                height=55,
                                style=ft.ButtonStyle(
                                    bgcolor="#2D3924",
                                    color="white",
                                    shape=ft.RoundedRectangleBorder(radius=5),
                                )
                            ),
                            ft.Container(height=10),
                            ft.Text(
                                "Em desenvolvimento",
                                size=11,
                                color="grey400"
                            )
                        ],
                        horizontal_alignment="center",
                        spacing=10
                    )
                )
            )
        )

    page.add(build_login_view()) 

    # --- ADICIONE ESTE BLOCO PARA LOGIN AUTOMÁTICO NO DESENVOLVIMENTO ---
    # TÉCNICO: Injetamos um usuário diretamente na sessão do Flet
    # Isso simula um login bem-sucedido no PostgreSQL 17 sem precisar digitar nada
    #mock_user = {
     #   "id": 1, 
      #  "nome": "SGT Lucas (MODO DEV)", 
       # "email": "sgtlucas@salc.com", 
        #"is_admin": True
    #}
    
    #page.session.set("user", mock_user)
    #_load_global_caches(page) # Carrega os PIs e NDs do banco local
    #show_main_layout()        # Pula direto para a tela principal
    
   
    page.update() # ESSA LINHA É ESSENCIAL PARA SAIR DO CARREGAMENTO INFINITO

if __name__ == "__main__":
    # TÉCNICO: '0.0.0.0' permite que o servidor aceite conexões de outros PCs na rede
    # O PostgreSQL 17 local lidará com as requisições simultâneas com alta performance
    
    port = int(os.environ.get("PORT", 8550))
    
    print(f"A iniciar servidor web na porta: {port}")
    
    ft.app(
        upload_dir="uploads",
        target=main,
        view=ft.AppView.WEB_BROWSER, # FORÇA a abertura no navegador
        host="0.0.0.0",               # LIBERA o acesso para outros IPs da rede
        port=port
    )
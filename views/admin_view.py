# views/admin_view.py
# (Versão Refatorada v1.5 - Layout Moderno)
# (Corrige a lógica de exibição de 'Quem' nos logs)

import flet as ft
import traceback
from datetime import datetime
import database # TÉCNICO: Motor de conexão PostgreSQL 17 local

class AdminView(ft.Row): 
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        # TÉCNICO: Retiramos o expand=True para não conflitar com o scroll do main.py
        self.alignment = ft.MainAxisAlignment.START
        self.vertical_alignment = ft.CrossAxisAlignment.START 
        self.spacing = 20
        self.error_modal = error_modal
        
        self.user_id_to_login_map = {}
        
        # --- 1. Inicialização dos Componentes (Construção dos Objetos) ---
        self.progress_ring_users = ft.ProgressRing(visible=False, width=32, height=32)
        self.tabela_users = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Login (Email)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nome Completo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Função", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        self.progress_ring_secoes = ft.ProgressRing(visible=False, width=32, height=32)
        self.txt_nova_secao = ft.TextField(label="Nome da Nova Seção", expand=True)
        self.btn_add_secao = ft.IconButton(
            icon="ADD", 
            on_click=self.add_secao,
            tooltip="Adicionar Seção"
        )
        self.lista_secoes_view = ft.ListView(expand=True, spacing=10)
        
        self.progress_ring_logs = ft.ProgressRing(visible=False, width=32, height=32)
        self.tabela_logs = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Quando", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Quem", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Ação", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
            heading_row_height=50,
            data_row_min_height=60, 
            column_spacing=15,
        )
        
        # --- 2. Definição dos Modais ---
        self.modal_add_login = ft.TextField(label="Login", prefix_text="@salc.com")
        self.modal_add_senha = ft.TextField(label="Senha Temporária", password=True, can_reveal_password=True)
        self.modal_add_nome = ft.TextField(label="Nome Completo")
        self.modal_add_funcao = ft.Dropdown(
            label="Função",
            options=[ft.dropdown.Option("usuario", "Utilizador Padrão"), ft.dropdown.Option("admin", "Administrador")],
            value="usuario"
        )
        self.modal_add_user = ft.AlertDialog(
            modal=True, title=ft.Text("Adicionar Novo Utilizador"),
            content=ft.Column([self.modal_add_login, self.modal_add_senha, self.modal_add_nome, self.modal_add_funcao], height=320, width=400),
            actions=[ft.TextButton("Cancelar", on_click=self.close_add_modal), ft.ElevatedButton("Criar", on_click=self.save_new_user)],
        )

        self.modal_edit_nome = ft.TextField(label="Nome Completo")
        self.modal_edit_funcao = ft.Dropdown(
            label="Função",
            options=[ft.dropdown.Option("usuario", "Utilizador Padrão"), ft.dropdown.Option("admin", "Administrador")]
        )
        self.modal_edit_user = ft.AlertDialog(
            modal=True, title=ft.Text("Editar Dados do Utilizador"),
            content=ft.Column([self.modal_edit_nome, self.modal_edit_funcao], height=220, width=400),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: setattr(self.modal_edit_user, "open", False) or self.page.update()),
                ft.ElevatedButton("Salvar", icon="SAVE", on_click=self.save_edit_user)
            ],
        )
        
        self.confirm_delete_user_dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirmar Exclusão"),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_confirm_delete_user),
                ft.ElevatedButton("Excluir", color="white", bgcolor="red", on_click=self.confirm_delete_user),
            ],
        )
        
        # --- 3. Montagem dos Cards (Uso dos objetos criados acima) ---
        self.layout_gestao_users = ft.Card(
            elevation=4,
            content=ft.Container(padding=20, content=ft.Column([
                ft.Row([ft.Text("Gestão de Utilizadores", size=20, weight="bold"), self.progress_ring_users], alignment="spaceBetween"),
                ft.ElevatedButton("Adicionar Novo Utilizador", icon="ADD", on_click=self.open_add_modal),
                ft.Divider(),
                self.tabela_users
            ], height=450))
        )
        
        self.layout_gestao_secoes = ft.Card(
            elevation=4,
            content=ft.Container(padding=20, content=ft.Column([
                ft.Row([ft.Text("Gestão de Seções", size=20, weight="bold"), self.progress_ring_secoes], alignment="spaceBetween"),
                ft.Row([self.txt_nova_secao, self.btn_add_secao]),
                ft.Divider(),
                self.lista_secoes_view
            ], height=300))
        )

        self.layout_gestao_logs = ft.Card(
            elevation=4, expand=True,
            content=ft.Container(padding=20, content=ft.Column([
                ft.Row([ft.Text("Logs de Auditoria", size=20, weight="bold"), ft.IconButton("REFRESH", on_click=self.load_logs_wrapper)], alignment="spaceBetween"),
                ft.Divider(),
                self.tabela_logs
            ], expand=True))
        )

        # --- 4. Montagem Final do Layout ---
        self.controls = [
            ft.Column([self.layout_gestao_users, self.layout_gestao_secoes], expand=6, spacing=20),
            ft.Column([self.layout_gestao_logs], expand=4)
        ]

        # TÉCNICO: Inserção no overlay para funcionamento dos modais
        self.page.overlay.extend([self.modal_add_user, self.confirm_delete_user_dialog, self.modal_edit_user])
        
        # Chamada de montagem
        self.on_mount = self.on_view_mount
         
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("AdminView: Controlo montado. A carregar dados...")
        self.load_users()
        self.load_secoes()
        self.load_logs() 


    def load_users_wrapper(self, e):
        """Wrapper para o botão de refresh."""
        self.load_users()

    def load_users(self):
        """Carrega utilizadores e atribui dados aos ícones."""
        self.progress_ring_users.visible = True
        if self.page: self.update()
        try:
            sql = "SELECT id_usuario, email, nome_completo, funcao FROM perfis_usuarios ORDER BY nome_completo"
            perfis = database.execute_query(sql)
            self.tabela_users.rows.clear()
            self.user_id_to_login_map.clear()

            if perfis:
                for p in perfis:
                    u_id = p['id_usuario']
                    u_login = p['email'].split('@')[0]
                    self.user_id_to_login_map[u_id] = u_login

                    self.tabela_users.rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(u_login)),
                            ft.DataCell(ft.Text(p['nome_completo'] or "")),
                            ft.DataCell(ft.Text(p['funcao'])),
                            ft.DataCell(
                                ft.Row([
                                    # TÉCNICO: Usamos Container para simular o 'botão de teste' que funcionou
                                    ft.Container(
                                        content=ft.Icon(ft.icons.EDIT, color="blue", size=20),
                                        on_click=self.handle_edit_click,
                                        data={"id": u_id, "login": u_login},
                                        padding=10
                                    ),
                                    ft.Container(
                                        content=ft.Icon(ft.icons.DELETE, color="red", size=20),
                                        on_click=self.handle_delete_click,
                                        data={"id": u_id, "login": u_login},
                                        padding=10
                                    ),
                                ])
                            ),
                        ])
                    )
            if self.page: self.update()
        except Exception as ex:
            print(f"Erro ao carregar utilizadores: {ex}")
        finally:
            self.progress_ring_users.visible = False
            if self.page: self.update()

    def handle_edit_click(self, e):
        """Ponte de comando que lê os dados do container."""
        user_data = e.control.data
        print(f"[DEBUG] Clique detectado para utilizador: {user_data['login']}")
        self.open_edit_user(user_data["id"], user_data["login"])

    # PONTES DE COMANDO (Handler): Indispensáveis para o clique funcionar
    def handle_edit_click(self, e):
        """Handler de depuração para confirmar o clique."""
        user_data = e.control.data
        print(f"\n[DEBUG] CLIQUE NO LÁPIS DETECTADO! Usuário: {user_data['login']}")
        self.open_edit_user(user_data["id"], user_data["login"])

    def handle_delete_click(self, e):
        """Gatilho para abrir a confirmação de exclusão."""
        user_data = e.control.data
        self.open_confirm_delete_user(user_data["id"], user_data["login"])

    # --- Funções de Gestão de Seções (sem alteração) ---
    def load_secoes_wrapper(self, e):
        self.load_secoes()

    def open_edit_user(self, user_id, user_login):
        """Busca dados e preenche o modal de edição."""
        try:
            res = database.execute_query("SELECT nome_completo, funcao FROM perfis_usuarios WHERE id_usuario = %s", (user_id,))
            if res:
                self.modal_edit_nome.value = res[0]['nome_completo']
                self.modal_edit_funcao.value = res[0]['funcao']
                self.modal_edit_user.data = {"id": user_id, "login": user_login}
                self.modal_edit_user.open = True
                self.page.update()
        except Exception as ex:
            self.show_error(f"Erro ao carregar dados: {ex}")

    def save_edit_user(self, e):
        """Persiste a edição e grava o log de auditoria."""
        data = self.modal_edit_user.data
        if not data: return
        
        nome = self.modal_edit_nome.value.strip()
        funcao = self.modal_edit_funcao.value
        admin = self.page.session.get("user")

        try:
            database.execute_query("UPDATE perfis_usuarios SET nome_completo=%s, funcao=%s WHERE id_usuario=%s", (nome, funcao, data['id']))
            database.execute_query("UPDATE usuarios SET nome=%s, is_admin=%s WHERE id=%s", (nome, funcao == "admin", data['id']))
            
            database.registrar_log(admin.get('id'), "EDITAR", "usuarios", data['id'], f"Editou utilizador {data['login']}: {funcao}")
            
            self.show_success_snackbar(f"Utilizador {data['login']} atualizado!")
            self.modal_edit_user.open = False
            self.load_users(); self.load_logs()
        except Exception as ex:
            self.show_error(f"Falha ao salvar: {ex}")

    def load_secoes(self):
        """Busca a lista de seções no banco local."""
        print("AdminView: A carregar seções locais...")
        self.progress_ring_secoes.visible = True
        if self.page: self.update()
        
        try:
            resposta = database.execute_query("SELECT id, nome FROM secoes ORDER BY nome")
            
            self.lista_secoes_view.controls.clear()
            if resposta:
                for secao in resposta:
                    self.lista_secoes_view.controls.append(
                        ft.Row(
                            [
                                ft.Text(secao['nome'], expand=True),
                                ft.IconButton(
                                    icon="DELETE_OUTLINE", 
                                    icon_color="red700",
                                    tooltip="Excluir Seção",
                                    data=secao['id'], 
                                    on_click=self.delete_secao
                                )
                            ]
                        )
                    )
            else:
                self.lista_secoes_view.controls.append(ft.Text("Nenhuma seção cadastrada.", italic=True))
        except Exception as ex:
            self.handle_db_error(ex, "carregar seções")
        finally:
            self.progress_ring_secoes.visible = False
            if self.page: self.update()

    def add_secao(self, e):
        nome = self.txt_nova_secao.value.strip()
        if not nome:
            self.show_error("Falha: O nome da seção não pode estar vazio.")
            return

        user = self.page.session.get("user")
        try:
            # TÉCNICO: RETURNING id garante que o log tenha a referência correta
            res = database.execute_query("INSERT INTO secoes (nome) VALUES (%s) RETURNING id", (nome,))
            
            if res:
                # Registro do log detalhado via função global
                database.registrar_log(
                    user_id=user.get('id'),
                    acao="INSERIR",
                    tabela="secoes",
                    registro_id=res[0]['id'],
                    detalhes=f"Seção cadastrada: {nome}"
                )
                
                self.show_success_snackbar(f"Sucesso: Seção '{nome}' integrada ao sistema.")
                self.txt_nova_secao.value = ""
                self.load_secoes()
                self.load_logs()
        except Exception as ex:
            self.show_error(f"Negação: Não foi possível salvar a seção. Erro: {ex}")

    def delete_secao(self, e):
        secao_id = e.control.data
        admin = self.page.session.get("user")
        try:
            # Busca o nome antes de apagar para o log
            nome_res = database.execute_query("SELECT nome FROM secoes WHERE id = %s", (secao_id,))
            nome_secao = nome_res[0]['nome'] if nome_res else "Desconhecida"
            
            database.execute_query("DELETE FROM secoes WHERE id = %s", (secao_id,))
            
            # Registro de auditoria
            database.registrar_log(admin.get('id'), "EXCLUIR", "secoes", secao_id, f"Removeu a seção: {nome_secao}")
            
            self.show_success_snackbar(f"Seção '{nome_secao}' removida permanentemente.")
            self.load_secoes(); self.load_logs()
        except Exception as ex:
            self.show_error(f"Não foi possível excluir a seção: {ex}")

    # --- (INÍCIO DA CORREÇÃO v1.5) ---
    def load_logs_wrapper(self, e):
        """Força a recarga dos utilizadores e depois dos logs."""
        self.load_users() # Garante que os nomes apareçam corretamente nos logs
        self.load_logs()
        
    def load_logs(self):
        """Carrega logs com largura fixa para evitar estouro visual."""
        self.progress_ring_logs.visible = True
        self.update()
        try:
            sql = "SELECT created_at, user_id, action, detalhes FROM audit_logs ORDER BY created_at DESC LIMIT 50"
            resposta = database.execute_query(sql)
            self.tabela_logs.rows.clear()
            
            if resposta:
                for log in resposta:
                    data_f = datetime.fromisoformat(str(log['created_at'])).strftime('%d/%m %H:%M')
                    login_u = self.user_id_to_login_map.get(log['user_id'], f"ID: {log['user_id']}")
                    acao_desc = log.get('detalhes') or str(log['action'])

                    self.tabela_logs.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(data_f, size=11)),
                                ft.DataCell(ft.Text(login_u, size=11, weight="bold")),
                                ft.DataCell(
                                    ft.Container(
                                        # TÉCNICO: A largura fixa força a quebra de linha
                                        content=ft.Text(acao_desc, size=11),
                                        width=250, 
                                        padding=ft.padding.symmetric(vertical=5)
                                    )
                                )
                            ]
                        )
                    )
            self.update()
        except Exception as ex:
            print(f"Erro ao carregar logs: {ex}")
        finally:
            self.progress_ring_logs.visible = False
            self.update()
    # --- (FIM DA CORREÇÃO v1.5) ---

    def show_success_snackbar(self, message):
        """Exibe uma mensagem verde de sucesso no fundo da tela."""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor="green",
            duration=3000
        )
        self.page.snack_bar.open = True
        self.page.update()

    def show_error(self, message):
        """Exibe uma mensagem vermelha de erro ou negação no fundo da tela."""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color="white"),
            bgcolor="red",
            duration=5000
        )
        self.page.snack_bar.open = True
        self.page.update()

    # --- Funções do Modal de Adicionar Utilizador (sem alteração) ---
    def open_add_modal(self, e):
        self.modal_add_login.value = ""
        self.modal_add_senha.value = ""
        self.modal_add_nome.value = ""
        self.modal_add_funcao.value = "usuario"
        self.modal_add_login.error_text = None
        self.modal_add_senha.error_text = None
        self.modal_add_nome.error_text = None
        self.modal_add_user.open = True
        self.page.update()
        self.modal_add_login.focus()

    def close_add_modal(self, e):
        self.modal_add_user.open = False
        self.page.update()

    def save_new_user(self, e):
        login = self.modal_add_login.value.strip()
        senha = self.modal_add_senha.value
        nome = self.modal_add_nome.value.strip()
        funcao = self.modal_add_funcao.value
        admin_atual = self.page.session.get("user")

        if not all([login, senha, nome]):
            self.show_error("Ação Negada: Todos os campos são obrigatórios.")
            return

        import hashlib
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        email_f = f"{login}@salc.com"

        try:
            # 1. Criação do utilizador principal
            res_u = database.execute_query(
                "INSERT INTO usuarios (email, nome, senha_hash, is_admin) VALUES (%s, %s, %s, %s) RETURNING id",
                (email_f, nome, senha_hash, (funcao == 'admin'))
            )
            
            if res_u:
                novo_id = res_u[0]['id']
                # 2. Criação do perfil detalhado
                database.execute_query(
                    "INSERT INTO perfis_usuarios (id_usuario, email, nome_completo, funcao) VALUES (%s, %s, %s, %s)",
                    (novo_id, email_f, nome, funcao)
                )
                
                # 3. Registro de auditoria detalhado
                database.registrar_log(
                    user_id=admin_atual.get('id'),
                    acao="CRIAR_USER",
                    tabela="usuarios",
                    registro_id=novo_id,
                    detalhes=f"Novo utilizador: {login} | Perfil: {funcao} | Nome: {nome}"
                )
                
                self.show_success_snackbar(f"Sucesso: Utilizador '{login}' criado e ativo.")
                self.close_add_modal(None)
                self.load_users()
                self.load_logs()
        except Exception as ex:
            self.show_error(f"Erro Crítico: Falha ao persistir novo utilizador. Detalhes: {ex}")

    
    # --- Funções de Exclusão de Utilizador ---
    def open_confirm_delete_user(self, user_id, user_login):
        """Abre o modal de confirmação de exclusão."""
        print(f"A pedir confirmação para excluir utilizador: {user_login} (ID: {user_id})")
        self.confirm_delete_user_dialog.data = {"id": user_id, "login": user_login} 
        self.confirm_delete_user_dialog.content = ft.Text(f"Atenção!\nTem a certeza de que deseja excluir o utilizador '{user_login}'?\nEsta ação não pode ser desfeita.")
        self.page.dialog = self.confirm_delete_user_dialog 
        self.confirm_delete_user_dialog.open = True
        self.page.update()

    def close_confirm_delete_user(self, e):
        self.confirm_delete_user_dialog.open = False
        self.page.update()

    def confirm_delete_user(self, e):
        user_data = self.confirm_delete_user_dialog.data
        if not user_data: return
        
        admin_atual = self.page.session.get("user")
        u_id = user_data.get("id")
        u_login = user_data.get("login")

        try:
            # 1. Log de auditoria pré-exclusão
            database.registrar_log(
                user_id=admin_atual.get('id'),
                acao="EXCLUIR",
                tabela="usuarios",
                registro_id=u_id,
                detalhes=f"Exclusão definitiva: Utilizador {u_login} (ID: {u_id}) removido."
            )
            
            # 2. Remoção física no PostgreSQL 17
            database.execute_query("DELETE FROM usuarios WHERE id = %s", (u_id,))
            
            self.show_success_snackbar(f"Removido: O utilizador '{u_login}' não tem mais acesso.")
            self.close_confirm_delete_user(None)
            self.load_users()
            self.load_logs()
        except Exception as ex:
            self.show_error(f"Erro na Exclusão: Não foi possível remover o utilizador. {ex}")

    def show_error(self, message):
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Traduz erros do PostgreSQL 17 local para o Administrador."""
        msg = str(ex).lower()
        print(f"Erro Administrativo ({context}): {msg}") 
        
        if "foreign key" in msg:
            self.show_error("Erro de Integridade: Este item está vinculado a outros registros (ex: logs ou NCs) e não pode ser apagado.")
        elif "unique constraint" in msg:
            self.show_error("Erro: Já existe um registro com este identificador ou nome.")
        elif "connection" in msg:
            self.show_error("Erro de Conexão: O servidor PostgreSQL 17 local está inacessível.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {ex}")

    def show_success_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_admin_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa AdminView como um controlo Flet padrão.
    """
    return AdminView(page, error_modal=error_modal)
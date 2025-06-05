# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
from datetime import datetime
import io
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import pandas as pd
import json
from werkzeug.security import generate_password_hash, check_password_hash
from src.utils import formatar_data_brasileira  # Importando a função de formatação de data

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ean_app_secret_key_default")

# Registrar filtro Jinja2 para formatação de data brasileira
@app.template_filter("data_brasileira")
def data_brasileira_filter(data):
    if isinstance(data, str):
        try:
            # Tenta converter string ISO para datetime se necessário
            data_dt = datetime.fromisoformat(data)
            return formatar_data_brasileira(data_dt)
        except ValueError:
            return data # Retorna a string original se não for formato ISO
    elif isinstance(data, datetime):
        return formatar_data_brasileira(data)
    return data

# Configuração do banco de dados SQLite
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "produtos.db")
print(f"Usando banco de dados SQLite em: {DATABASE_PATH}")

# Função auxiliar para obter conexão SQLite
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Retorna linhas como dicionários
    # Habilitar chaves estrangeiras
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Inicializar o banco de dados (adaptado para SQLite)
def init_database():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Tabela de usuários
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                admin INTEGER DEFAULT 0
            );
            """)
            
            # Tabela de responsáveis com PIN
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS responsaveis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                pin TEXT NOT NULL
            );
            """)
            
            # Tabela de produtos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ean TEXT NOT NULL,
                nome TEXT NOT NULL,
                cor TEXT,
                voltagem TEXT,
                modelo TEXT,
                quantidade INTEGER NOT NULL,
                usuario_id INTEGER NOT NULL,
                timestamp TEXT, -- SQLite usa TEXT para DATETIME
                enviado INTEGER DEFAULT 0,
                data_envio TEXT,
                validado INTEGER DEFAULT 0,
                validador_id INTEGER,
                data_validacao TEXT,
                responsavel_id INTEGER,
                responsavel_pin TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
                FOREIGN KEY (validador_id) REFERENCES usuarios (id),
                FOREIGN KEY (responsavel_id) REFERENCES responsaveis (id)
            );
            """)
            
            # Verificar se já existe um admin APENAS se a tabela estiver vazia
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                 # Criar um usuário admin padrão
                admin_hash = generate_password_hash("admin")
                cursor.execute("INSERT INTO usuarios (nome, senha_hash, admin) VALUES (?, ?, ?)", 
                              ("admin", admin_hash, 1))
                conn.commit() # Commit necessário após INSERT
            
            # Inicializar responsáveis com PINs
            inicializar_responsaveis(conn) # Passar a conexão
                
        print("Banco de dados SQLite inicializado com sucesso.")
    except sqlite3.Error as e:
        print(f"Erro ao inicializar o banco de dados SQLite: {e}")

# Inicializar responsáveis com PINs (adaptado para SQLite)
def inicializar_responsaveis(conn):
    try:
        cursor = conn.cursor()
        # Verificar se já existem responsáveis
        cursor.execute("SELECT COUNT(*) FROM responsaveis")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Inserir responsáveis com seus PINs
            responsaveis = [
                ("Liliane", "5584"),
                ("Rogerio", "9841"),
                ("Celso", "2122"),
                ("Marcos", "6231")
            ]
            
            cursor.executemany("INSERT INTO responsaveis (nome, pin) VALUES (?, ?)", responsaveis)
            conn.commit() # Commit necessário
            print(f"Responsáveis inicializados: {len(responsaveis)}")
    except sqlite3.Error as e:
        print(f"Erro ao inicializar responsáveis: {e}")
        conn.rollback()

# Obter todos os responsáveis (adaptado para SQLite)
def obter_responsaveis():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome FROM responsaveis ORDER BY nome")
            responsaveis = [dict(row) for row in cursor.fetchall()]
        return responsaveis
    except sqlite3.Error as e:
        print(f"Erro ao obter responsáveis: {e}")
        return []

# Verificar PIN do responsável (adaptado para SQLite)
def verificar_pin_responsavel(responsavel_id, pin):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pin FROM responsaveis WHERE id = ?", (responsavel_id,))
            resultado = cursor.fetchone()
            
            if resultado and resultado["pin"] == pin:
                return True
            return False
    except sqlite3.Error as e:
        print(f"Erro ao verificar PIN do responsável: {e}")
        return False

# Obter nome do responsável (adaptado para SQLite)
def obter_nome_responsavel(responsavel_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM responsaveis WHERE id = ?", (responsavel_id,))
            resultado = cursor.fetchone()
            
            if resultado:
                return resultado["nome"]
            return None
    except sqlite3.Error as e:
        print(f"Erro ao obter nome do responsável: {e}")
        return None

# Funções de autenticação (adaptadas para SQLite)
def registrar_usuario(nome, senha):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            senha_hash = generate_password_hash(senha)
            cursor.execute("INSERT INTO usuarios (nome, senha_hash) VALUES (?, ?)", (nome, senha_hash))
            conn.commit()
        return True
    except sqlite3.IntegrityError: # Erro específico para UNIQUE constraint
        # Nome de usuário já existe
        return False
    except sqlite3.Error as e:
        print(f"Erro ao registrar usuário: {e}")
        conn.rollback()
        return False

def verificar_usuario(nome, senha):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, senha_hash, admin FROM usuarios WHERE nome = ?", (nome,))
            usuario = cursor.fetchone()
        
        if usuario and check_password_hash(usuario["senha_hash"], senha):
            # Retornar como dicionário
            return {"id": usuario["id"], "admin": usuario["admin"]}
        return None
    except sqlite3.Error as e:
        print(f"Erro ao verificar usuário: {e}")
        return None

def obter_nome_usuario(usuario_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM usuarios WHERE id = ?", (usuario_id,))
            usuario = cursor.fetchone()
        return usuario["nome"] if usuario else None
    except sqlite3.Error as e:
        print(f"Erro ao obter nome do usuário: {e}")
        return None

# Funções de produtos (adaptadas para SQLite)
def carregar_produtos_usuario(usuario_id, apenas_nao_enviados=False):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if apenas_nao_enviados:
                cursor.execute("SELECT * FROM produtos WHERE usuario_id = ? AND enviado = 0 ORDER BY timestamp DESC", (usuario_id,))
            else:
                cursor.execute("SELECT * FROM produtos WHERE usuario_id = ? ORDER BY timestamp DESC", (usuario_id,))
            produtos = [dict(row) for row in cursor.fetchall()]
        return produtos
    except sqlite3.Error as e:
        print(f"Erro ao carregar produtos do usuário: {e}")
        return []

def carregar_todas_listas_enviadas():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Buscar produtos enviados junto com o nome do usuário, do validador e do responsável (se houver)
            cursor.execute("""
            SELECT p.*, 
                   u.nome as nome_usuario,
                   v.nome as nome_validador,
                   r.nome as nome_responsavel
            FROM produtos p 
            JOIN usuarios u ON p.usuario_id = u.id 
            LEFT JOIN usuarios v ON p.validador_id = v.id
            LEFT JOIN responsaveis r ON p.responsavel_id = r.id
            WHERE p.enviado = 1 
            ORDER BY p.data_envio DESC
            """)
            produtos = [dict(row) for row in cursor.fetchall()]
        return produtos
    except sqlite3.Error as e:
        print(f"Erro ao carregar todas as listas enviadas: {e}")
        return []

def pesquisar_produtos(termo_pesquisa):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Usar LIKE para busca case-insensitive no SQLite (pode precisar de LOWER() para garantir)
            termo_like = f"%{termo_pesquisa}%"
            cursor.execute("""
            SELECT p.*, 
                   u.nome as nome_usuario,
                   v.nome as nome_validador,
                   r.nome as nome_responsavel
            FROM produtos p 
            JOIN usuarios u ON p.usuario_id = u.id 
            LEFT JOIN usuarios v ON p.validador_id = v.id
            LEFT JOIN responsaveis r ON p.responsavel_id = r.id
            WHERE p.enviado = 1 
              AND (p.ean LIKE ? OR 
                   LOWER(p.nome) LIKE LOWER(?) OR 
                   LOWER(p.cor) LIKE LOWER(?) OR 
                   LOWER(p.modelo) LIKE LOWER(?))
            ORDER BY p.data_envio DESC
            """, (termo_like, termo_like, termo_like, termo_like))
            produtos = [dict(row) for row in cursor.fetchall()]
        return produtos
    except sqlite3.Error as e:
        print(f"Erro ao pesquisar produtos: {e}")
        return []

def buscar_produto_local(ean, usuario_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0", (ean, usuario_id))
            produto = cursor.fetchone()
        return dict(produto) if produto else None
    except sqlite3.Error as e:
        print(f"Erro ao buscar produto local: {e}")
        return None

def salvar_produto(produto, usuario_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Verificar se o produto já existe para este usuário e não foi enviado
            cursor.execute("SELECT id, quantidade FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0", 
                          (produto["ean"], usuario_id))
            existing = cursor.fetchone()
            
            # Garantir que timestamp seja uma string no formato ISO
            timestamp_str = datetime.now().isoformat()

            if existing:
                # Atualizar quantidade
                nova_quantidade = existing["quantidade"] + produto["quantidade"]
                cursor.execute("""
                UPDATE produtos 
                SET quantidade = ?, 
                    timestamp = ? 
                WHERE id = ?
                """, (nova_quantidade, timestamp_str, existing["id"]))
            else:
                # Inserir novo produto
                cursor.execute("""
                INSERT INTO produtos (ean, nome, cor, voltagem, modelo, quantidade, usuario_id, timestamp, enviado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    produto["ean"], 
                    produto["nome"], 
                    produto.get("cor"), 
                    produto.get("voltagem"), 
                    produto.get("modelo"), 
                    produto["quantidade"], 
                    usuario_id,
                    timestamp_str
                ))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao salvar produto: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"Erro inesperado ao salvar produto: {e}")
        return False

def enviar_lista_produtos(usuario_id, responsavel_id, pin):
    try:
        # Verificar se o PIN corresponde ao responsável
        if not verificar_pin_responsavel(responsavel_id, pin):
            print(f"PIN inválido para o responsável ID {responsavel_id}")
            flash("PIN do responsável inválido.", "error")
            return False # Indicar falha
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            data_envio_str = datetime.now().isoformat()
            # Marcar todos os produtos não enviados como enviados
            cursor.execute("""
            UPDATE produtos 
            SET enviado = 1, 
                data_envio = ?, 
                responsavel_id = ?, 
                responsavel_pin = ?
            WHERE usuario_id = ? AND enviado = 0
            """, (data_envio_str, responsavel_id, pin, usuario_id))
            
            affected_rows = cursor.rowcount
            conn.commit()
            
            if affected_rows > 0:
                print(f"{affected_rows} produtos marcados como enviados para usuário {usuario_id}")
                return True # Indicar sucesso
            else:
                print(f"Nenhum produto para enviar para usuário {usuario_id}")
                flash("Nenhum produto na lista atual para enviar.", "warning")
                return False # Indicar que nada foi enviado

    except sqlite3.Error as e:
        print(f"Erro ao enviar lista de produtos: {e}")
        conn.rollback()
        flash("Erro ao enviar a lista. Tente novamente.", "error")
        return False
    except Exception as e:
        print(f"Erro inesperado ao enviar lista: {e}")
        flash("Erro inesperado ao enviar a lista.", "error")
        return False

def validar_produto(produto_id, validador_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            data_validacao_str = datetime.now().isoformat()
            cursor.execute("""
            UPDATE produtos 
            SET validado = 1, 
                validador_id = ?, 
                data_validacao = ?
            WHERE id = ? AND enviado = 1
            """, (validador_id, data_validacao_str, produto_id))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao validar produto: {e}")
        conn.rollback()
        return False

def excluir_produto(produto_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
            conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao excluir produto: {e}")
        conn.rollback()
        return False

# --- Rotas Flask ---

@app.route("/")
def index():
    if "usuario_id" not in session:
        return redirect(url_for("login"))
    
    usuario_id = session["usuario_id"]
    produtos_usuario = carregar_produtos_usuario(usuario_id, apenas_nao_enviados=True)
    responsaveis = obter_responsaveis()
    
    return render_template("index.html", produtos=produtos_usuario, responsaveis=responsaveis)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        usuario = verificar_usuario(nome, senha)
        
        if usuario:
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = nome
            session["admin"] = usuario["admin"]
            flash("Login realizado com sucesso!", "success")
            if usuario["admin"]:
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("index"))
        else:
            flash("Nome de usuário ou senha inválidos.", "error")
            
    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        
        if registrar_usuario(nome, senha):
            flash("Usuário registrado com sucesso! Faça o login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Nome de usuário já existe ou ocorreu um erro.", "error")
            
    return render_template("registro.html")

@app.route("/logout")
def logout():
    session.pop("usuario_id", None)
    session.pop("usuario_nome", None)
    session.pop("admin", None)
    flash("Você foi desconectado.", "info")
    return redirect(url_for("login"))

@app.route("/admin")
def admin():
    if "usuario_id" not in session or not session.get("admin"):
        flash("Acesso não autorizado.", "error")
        return redirect(url_for("login"))
        
    termo_pesquisa = request.args.get("q", "") # Pega o parâmetro de busca 'q'
    if termo_pesquisa:
        listas_enviadas = pesquisar_produtos(termo_pesquisa)
    else:
        listas_enviadas = carregar_todas_listas_enviadas()
    
    # Agrupar por usuário e data de envio para exibição
    listas_agrupadas = {}
    for produto in listas_enviadas:
        chave = (produto["nome_usuario"], produto["data_envio"])
        if chave not in listas_agrupadas:
            listas_agrupadas[chave] = []
        listas_agrupadas[chave].append(produto)
        
    return render_template("admin.html", listas_agrupadas=listas_agrupadas, termo_pesquisa=termo_pesquisa)

@app.route("/buscar_ean", methods=["POST"])
def buscar_ean_api():
    if "usuario_id" not in session:
        return jsonify({"error": "Não autenticado"}), 401
        
    ean = request.json.get("ean")
    if not ean:
        return jsonify({"error": "EAN não fornecido"}), 400

    # 1. Buscar no banco de dados local do usuário (não enviados)
    produto_local = buscar_produto_local(ean, session["usuario_id"])
    if produto_local:
        # Se encontrado localmente, retorna os dados e indica que já existe
        return jsonify({
            "ean": produto_local["ean"],
            "nome": produto_local["nome"],
            "cor": produto_local.get("cor", ""),
            "voltagem": produto_local.get("voltagem", ""),
            "modelo": produto_local.get("modelo", ""),
            "quantidade_existente": produto_local["quantidade"],
            "local": True # Indica que foi encontrado localmente
        })

    # 2. Se não encontrado localmente, buscar na API externa (exemplo)
    # Substitua pela URL da sua API de busca de EAN
    api_url = f"https://api.example.com/ean/{ean}" # URL fictícia
    try:
        # Adicione headers ou autenticação se necessário
        response = requests.get(api_url, timeout=10)
        response.raise_for_status() # Lança erro para status >= 400
        data = response.json()
        
        # Adapte os campos conforme a resposta da sua API
        return jsonify({
            "ean": data.get("ean", ean),
            "nome": data.get("description", "Produto não encontrado"),
            "cor": data.get("color", ""),
            "voltagem": data.get("voltage", ""),
            "modelo": data.get("model", ""),
            "local": False
        })
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar EAN na API externa: {e}")
        # Retorna apenas o EAN para preenchimento manual
        return jsonify({"ean": ean, "nome": "", "cor": "", "voltagem": "", "modelo": "", "local": False, "error_api": str(e)})
    except Exception as e:
        print(f"Erro inesperado ao processar busca EAN: {e}")
        return jsonify({"error": "Erro interno ao buscar EAN"}), 500

@app.route("/adicionar_produto", methods=["POST"])
def adicionar_produto_api():
    if "usuario_id" not in session:
        return jsonify({"error": "Não autenticado"}), 401
        
    data = request.json
    ean = data.get("ean")
    nome = data.get("nome")
    quantidade = data.get("quantidade")

    if not ean or not nome or not quantidade:
        return jsonify({"error": "Dados incompletos"}), 400
        
    try:
        quantidade = int(quantidade)
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser positiva")
    except ValueError:
        return jsonify({"error": "Quantidade inválida"}), 400

    produto = {
        "ean": ean,
        "nome": nome,
        "cor": data.get("cor"),
        "voltagem": data.get("voltagem"),
        "modelo": data.get("modelo"),
        "quantidade": quantidade
    }
    
    if salvar_produto(produto, session["usuario_id"]):
        # Recarregar produtos para atualizar a interface
        produtos_atualizados = carregar_produtos_usuario(session["usuario_id"], apenas_nao_enviados=True)
        return jsonify({"success": True, "produtos": produtos_atualizados})
    else:
        return jsonify({"error": "Erro ao salvar produto"}), 500

@app.route("/enviar_lista", methods=["POST"])
def enviar_lista_api():
    if "usuario_id" not in session:
        return jsonify({"error": "Não autenticado"}), 401
        
    responsavel_id = request.form.get("responsavel_id")
    pin = request.form.get("pin")
    
    if not responsavel_id or not pin:
        flash("Selecione o responsável e digite o PIN.", "error")
        return redirect(url_for("index"))
        
    try:
        responsavel_id = int(responsavel_id)
    except ValueError:
        flash("ID do responsável inválido.", "error")
        return redirect(url_for("index"))

    sucesso = enviar_lista_produtos(session["usuario_id"], responsavel_id, pin)
    
    if sucesso:
        flash("Lista enviada com sucesso para o painel central!", "success")
    # Mensagens de erro/warning são tratadas dentro de enviar_lista_produtos
        
    return redirect(url_for("index"))

@app.route("/exportar_excel", methods=["POST"])
def exportar_excel():
    if "usuario_id" not in session or not session.get("admin"):
        return jsonify({"error": "Não autorizado"}), 403

    # Obter todos os produtos enviados (ou filtrados, se necessário)
    produtos_enviados = carregar_todas_listas_enviadas()
    
    if not produtos_enviados:
        flash("Nenhuma lista enviada para exportar.", "warning")
        # Poderia retornar um erro ou redirecionar
        return redirect(url_for("admin")) 

    # Preparar dados para o DataFrame
    dados_para_df = []
    for produto in produtos_enviados:
        dados_para_df.append({
            "EAN": produto["ean"],
            "DESCRIÇÃO": produto["nome"],
            "QUANTIDADE": produto["quantidade"],
            "USUÁRIO": produto["nome_usuario"],
            "DATA_ENVIO": formatar_data_brasileira(datetime.fromisoformat(produto["data_envio"])) if produto["data_envio"] else "",
            "VALIDADO": "Sim" if produto["validado"] else "Não",
            "VALIDADOR": produto["nome_validador"] if produto["validado"] else "",
            "DATA_VALIDACAO": formatar_data_brasileira(datetime.fromisoformat(produto["data_validacao"])) if produto["validado"] and produto["data_validacao"] else "",
            "RESPONSÁVEL": produto["nome_responsavel"] if produto["responsavel_id"] else ""
        })
        
    df = pd.DataFrame(dados_para_df)
    
    # Criar arquivo Excel na memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine=\'openpyxl\') as writer:
        df.to_excel(writer, index=False, sheet_name=\'Listas Enviadas\')
    output.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"listas_enviadas_{timestamp}.xlsx"
    
    return send_file(output, 
                     download_name=filename, 
                     as_attachment=True, 
                     mimetype=\'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\')

@app.route("/validar/<int:produto_id>", methods=["POST"])
def validar_api(produto_id):
    if "usuario_id" not in session or not session.get("admin"):
        return jsonify({"error": "Não autorizado"}), 403
        
    if validar_produto(produto_id, session["usuario_id"]):
        flash(f"Produto ID {produto_id} validado com sucesso.", "success")
    else:
        flash(f"Erro ao validar produto ID {produto_id}.", "error")
        
    # Redirecionar de volta para admin, preservando a busca se houver
    termo_pesquisa = request.referrer.split(\'q=\')[-1] if \'q=\' in request.referrer else \'\'
    return redirect(url_for("admin", q=termo_pesquisa))

@app.route("/excluir_produto/<int:produto_id>", methods=["POST"])
def excluir_produto_api(produto_id):
    # Permitir exclusão pelo próprio usuário (se não enviado) ou pelo admin
    if "usuario_id" not in session:
        return jsonify({"error": "Não autenticado"}), 401

    # Verificar se o produto pertence ao usuário e não foi enviado OU se é admin
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT usuario_id, enviado FROM produtos WHERE id = ?", (produto_id,))
            produto = cursor.fetchone()

        if not produto:
             flash("Produto não encontrado.", "error")
             return redirect(request.referrer or url_for(\'index\'))

        is_admin = session.get("admin", 0)
        is_owner_not_sent = (produto["usuario_id"] == session["usuario_id"] and not produto["enviado"])

        if not is_admin and not is_owner_not_sent:
            flash("Você não tem permissão para excluir este produto.", "error")
            return redirect(request.referrer or url_for(\'index\'))

        # Se chegou aqui, tem permissão para excluir
        if excluir_produto(produto_id):
            flash(f"Produto ID {produto_id} excluído com sucesso.", "success")
        else:
            flash(f"Erro ao excluir produto ID {produto_id}.", "error")

    except sqlite3.Error as e:
        flash(f"Erro de banco de dados ao tentar excluir: {e}", "error")
    except Exception as e:
        flash(f"Erro inesperado ao tentar excluir: {e}", "error")

    # Redirecionar de volta para a página anterior (index ou admin)
    # Tenta preservar a busca se estava no admin
    redirect_url = url_for("index")
    if request.referrer and \'/admin\' in request.referrer:
        termo_pesquisa = request.referrer.split(\'q=\')[-1] if \'q=\' in request.referrer else \'\'
        redirect_url = url_for("admin", q=termo_pesquisa)
    elif request.referrer:
        redirect_url = request.referrer
        
    return redirect(redirect_url)


if __name__ == "__main__":
    init_database() # Garante que o DB e as tabelas existam
    # app.run(debug=True) # debug=True não é recomendado para produção
    # Use a porta 5000 por padrão, escutando em todas as interfaces
    # O script iniciar_sistema.ps1 usará 'flask run'
    pass # A execução será feita pelo comando 'flask run' via script PowerShell


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

# Importar módulos locais
from .utils import formatar_data_brasileira
from . import mercado_livre # Importar o módulo da API Mercado Livre

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ean_app_secret_key_default_local") # Usar chave secreta padrão diferente para local

# Caminho para o banco de dados SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "produtos.db")

print(f"Usando banco de dados SQLite em: {DATABASE_PATH}")

# Registrar filtro Jinja2 para formatação de data brasileira
@app.template_filter("data_brasileira")
def data_brasileira_filter(data):
    if isinstance(data, str):
        try:
            data = datetime.fromisoformat(data)
        except ValueError:
            return data
    return formatar_data_brasileira(data)

# Função auxiliar para obter conexão SQLite
def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados SQLite: {e}")
        return None

# Inicializar o banco de dados (adaptado para SQLite)
def init_database():
    conn = get_db_connection()
    if not conn:
        print("Falha ao obter conexão com o banco de dados para inicialização.")
        return
    try:
        with conn:
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
                timestamp TEXT, -- Armazenar como TEXT ISO8601
                enviado INTEGER DEFAULT 0,
                data_envio TEXT, -- Armazenar como TEXT ISO8601
                validado INTEGER DEFAULT 0,
                validador_id INTEGER,
                data_validacao TEXT, -- Armazenar como TEXT ISO8601
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
                cursor.execute("SELECT * FROM usuarios WHERE admin = 1")
                admin_exists = cursor.fetchone()
                if not admin_exists:
                    admin_hash = generate_password_hash("admin")
                    cursor.execute("INSERT INTO usuarios (nome, senha_hash, admin) VALUES (?, ?, ?)", ("admin", admin_hash, 1))
            # Inicializar responsáveis com PINs (se não existirem)
            inicializar_responsaveis(conn)
        print("Banco de dados SQLite inicializado com sucesso.")
        # Verificar se o arquivo existe após a inicialização
        if os.path.exists(DATABASE_PATH):
            print("Arquivo de banco de dados encontrado.")
        else:
            print("Arquivo de banco de dados NÃO encontrado após inicialização.")
            
    except sqlite3.Error as e:
        print(f"Erro ao inicializar o banco de dados SQLite: {e}")
    finally:
        if conn:
            conn.close()

# Inicializar responsáveis com PINs (adaptado para SQLite)
def inicializar_responsaveis(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM responsaveis")
        count = cursor.fetchone()[0]
        if count == 0:
            responsaveis = [("Liliane", "5584"), ("Rogerio", "9841"), ("Celso", "2122"), ("Marcos", "6231")]
            cursor.executemany("INSERT INTO responsaveis (nome, pin) VALUES (?, ?)", responsaveis)
            print(f"Responsáveis inicializados: {len(responsaveis)}")
    except sqlite3.Error as e:
        print(f"Erro ao inicializar responsáveis: {e}")

# Obter todos os responsáveis (adaptado para SQLite)
def obter_responsaveis():
    responsaveis = []
    conn = get_db_connection()
    if not conn: return responsaveis
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome FROM responsaveis ORDER BY nome")
            responsaveis = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao obter responsáveis: {e}")
    finally:
        if conn: conn.close()
    # Converter para lista de dicionários para JSON
    return [dict(row) for row in responsaveis]

# Verificar PIN do responsável (adaptado para SQLite)
def verificar_pin_responsavel(responsavel_id, pin):
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pin FROM responsaveis WHERE id = ?", (responsavel_id,))
            resultado = cursor.fetchone()
            return bool(resultado and resultado["pin"] == pin)
    except sqlite3.Error as e:
        print(f"Erro ao verificar PIN do responsável: {e}")
        return False
    finally:
        if conn: conn.close()

# Obter nome do responsável (adaptado para SQLite)
def obter_nome_responsavel(responsavel_id):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM responsaveis WHERE id = ?", (responsavel_id,))
            resultado = cursor.fetchone()
            return resultado["nome"] if resultado else None
    except sqlite3.Error as e:
        print(f"Erro ao obter nome do responsável: {e}")
        return None
    finally:
        if conn: conn.close()

# Funções de autenticação (adaptadas para SQLite)
def registrar_usuario(nome, senha):
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn:
            cursor = conn.cursor()
            senha_hash = generate_password_hash(senha)
            cursor.execute("INSERT INTO usuarios (nome, senha_hash) VALUES (?, ?)", (nome, senha_hash))
        return True
    except sqlite3.IntegrityError: return False # Nome já existe
    except sqlite3.Error as e:
        print(f"Erro ao registrar usuário: {e}")
        return False
    finally:
        if conn: conn.close()

def verificar_usuario(nome, senha):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, senha_hash, admin FROM usuarios WHERE nome = ?", (nome,))
            usuario = cursor.fetchone()
        if usuario and check_password_hash(usuario["senha_hash"], senha):
            return dict(usuario)
        return None
    except sqlite3.Error as e:
        print(f"Erro ao verificar usuário: {e}")
        return None
    finally:
        if conn: conn.close()

def obter_nome_usuario(usuario_id):
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM usuarios WHERE id = ?", (usuario_id,))
            usuario = cursor.fetchone()
        return usuario["nome"] if usuario else None
    except sqlite3.Error as e:
        print(f"Erro ao obter nome do usuário: {e}")
        return None
    finally:
        if conn: conn.close()

# Funções de produtos (adaptadas para SQLite)
def carregar_produtos_usuario(usuario_id, apenas_nao_enviados=False):
    produtos = []
    conn = get_db_connection()
    if not conn: return produtos
    try:
        with conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM produtos WHERE usuario_id = ?"
            params = [usuario_id]
            if apenas_nao_enviados:
                sql += " AND enviado = 0"
            sql += " ORDER BY timestamp DESC"
            cursor.execute(sql, tuple(params))
            produtos = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao carregar produtos do usuário: {e}")
    finally:
        if conn: conn.close()
    return [dict(p) for p in produtos]

def carregar_todas_listas_enviadas():
    produtos = []
    conn = get_db_connection()
    if not conn: return produtos
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador, r.nome as nome_responsavel
            FROM produtos p JOIN usuarios u ON p.usuario_id = u.id 
            LEFT JOIN usuarios v ON p.validador_id = v.id
            LEFT JOIN responsaveis r ON p.responsavel_id = r.id
            WHERE p.enviado = 1 ORDER BY p.data_envio DESC
            """)
            produtos = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao carregar todas as listas enviadas: {e}")
    finally:
        if conn: conn.close()
    return [dict(p) for p in produtos]

def pesquisar_produtos(termo_pesquisa):
    produtos = []
    conn = get_db_connection()
    if not conn: return produtos
    try:
        with conn:
            cursor = conn.cursor()
            termo_like = f"%{termo_pesquisa}%"
            cursor.execute("""
            SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador, r.nome as nome_responsavel
            FROM produtos p JOIN usuarios u ON p.usuario_id = u.id 
            LEFT JOIN usuarios v ON p.validador_id = v.id
            LEFT JOIN responsaveis r ON p.responsavel_id = r.id
            WHERE p.enviado = 1 AND (p.ean LIKE ? OR p.nome LIKE ? OR p.cor LIKE ? OR p.modelo LIKE ?)
            ORDER BY p.data_envio DESC
            """, (termo_like, termo_like, termo_like, termo_like))
            produtos = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erro ao pesquisar produtos: {e}")
    finally:
        if conn: conn.close()
    return [dict(p) for p in produtos]

def buscar_produto_local(ean, usuario_id):
    produto = None
    conn = get_db_connection()
    if not conn: return None
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0", (ean, usuario_id))
            produto = cursor.fetchone()
    except sqlite3.Error as e:
        print(f"Erro ao buscar produto local: {e}")
    finally:
        if conn: conn.close()
    return dict(produto) if produto else None

def salvar_produto(produto, usuario_id):
    conn = get_db_connection()
    if not conn: return False
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM produtos WHERE ean = ? AND usuario_id = ? AND enviado = 0", (produto["ean"], usuario_id))
            existing = cursor.fetchone()
            timestamp_obj = produto.get("timestamp")
            if isinstance(timestamp_obj, datetime): timestamp_str = timestamp_obj.isoformat()
            elif isinstance(timestamp_obj, str): 
                try: timestamp_str = datetime.fromisoformat(timestamp_obj).isoformat()
                except ValueError: timestamp_str = datetime.now().isoformat()
            else: timestamp_str = datetime.now().isoformat()
            if existing:
                cursor.execute("UPDATE produtos SET quantidade = quantidade + ?, timestamp = ? WHERE ean = ? AND usuario_id = ? AND enviado = 0", 
                              (produto["quantidade"], timestamp_str, produto["ean"], usuario_id))
            else:
                cursor.execute("INSERT INTO produtos (ean, nome, cor, voltagem, modelo, quantidade, usuario_id, timestamp, enviado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)", 
                              (produto["ean"], produto["nome"], produto.get("cor"), produto.get("voltagem"), produto.get("modelo"), produto["quantidade"], usuario_id, timestamp_str))
        return True
    except sqlite3.Error as e:
        print(f"Erro ao salvar produto: {e}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao salvar produto: {e}")
        return False
    finally:
        if conn: conn.close()

def enviar_lista_produtos(usuario_id, responsavel_id, pin):
    conn = get_db_connection()
    if not conn: return False, "Erro de conexão com DB"
    try:
        # Verificar se o PIN corresponde ao responsável
        if not verificar_pin_responsavel(responsavel_id, pin):
            print(f"PIN inválido para o responsável ID {responsavel_id}")
            return False, "PIN do responsável inválido"
        with conn:
            cursor = conn.cursor()
            data_envio = datetime.now().isoformat()
            # Marcar todos os produtos não enviados como enviados
            cursor.execute("UPDATE produtos SET enviado = 1, data_envio = ?, responsavel_id = ?, responsavel_pin = ? WHERE usuario_id = ? AND enviado = 0", 
                          (data_envio, responsavel_id, pin, usuario_id))
            if cursor.rowcount > 0:
                print(f"{cursor.rowcount} produtos marcados como enviados para usuário {usuario_id} pelo responsável {responsavel_id}")
                return True, f"{cursor.rowcount} produtos enviados com sucesso."
            else:
                print(f"Nenhum produto pendente encontrado para enviar para usuário {usuario_id}")
                return False, "Nenhum produto pendente para enviar."
    except sqlite3.Error as e:
        print(f"Erro ao enviar lista de produtos: {e}")
        return False, "Erro no banco de dados ao enviar lista."
    finally:
        if conn: conn.close()

def validar_lista_produtos(produto_ids, validador_id):
    conn = get_db_connection()
    if not conn: return False, "Erro de conexão com DB"
    if not produto_ids: return False, "Nenhum produto selecionado para validar."
    try:
        with conn:
            cursor = conn.cursor()
            data_validacao = datetime.now().isoformat()
            placeholders = ",".join("?" * len(produto_ids))
            sql = f"UPDATE produtos SET validado = 1, data_validacao = ?, validador_id = ? WHERE id IN ({placeholders}) AND enviado = 1"
            params = [data_validacao, validador_id] + produto_ids
            cursor.execute(sql, tuple(params))
            if cursor.rowcount > 0:
                print(f"{cursor.rowcount} produtos validados pelo usuário {validador_id}")
                return True, f"{cursor.rowcount} produtos validados com sucesso."
            else:
                print(f"Nenhum produto correspondente encontrado ou já validado para IDs: {produto_ids}")
                return False, "Nenhum produto encontrado para validar ou já estavam validados."
    except sqlite3.Error as e:
        print(f"Erro ao validar lista de produtos: {e}")
        return False, "Erro no banco de dados ao validar lista."
    finally:
        if conn: conn.close()

# --- Rotas Flask ---
@app.route("/")
def index():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        usuario = verificar_usuario(nome, senha)
        if usuario:
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = nome
            session["is_admin"] = bool(usuario["admin"])
            flash("Login bem-sucedido!", "success")
            if session["is_admin"]:
                return redirect(url_for("admin_panel"))
            else:
                # Se não for admin, redireciona para a página principal (index.html)
                return redirect(url_for("index"))
        else:
            flash("Nome de usuário ou senha inválidos.", "danger")
            return redirect(url_for("index"))
    # Se for GET, redireciona para a index que mostra o formulário
    return redirect(url_for("index"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        senha = request.form["senha"]
        if registrar_usuario(nome, senha):
            flash("Usuário registrado com sucesso! Faça o login.", "success")
            return redirect(url_for("index"))
        else:
            flash("Nome de usuário já existe ou erro ao registrar.", "danger")
            return render_template("register.html")
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.pop("usuario_id", None)
    session.pop("usuario_nome", None)
    session.pop("is_admin", None)
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect(url_for("index"))
    usuario_id = session["usuario_id"]
    produtos = carregar_produtos_usuario(usuario_id, apenas_nao_enviados=True)
    # A lista de responsáveis será carregada via API
    return render_template("dashboard.html", produtos=produtos)

# --- Rotas da API (para chamadas AJAX do frontend) ---

@app.route("/api/responsaveis", methods=["GET"])
def api_get_responsaveis():
    if "usuario_id" not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401
    responsaveis = obter_responsaveis()
    return jsonify(responsaveis)

@app.route("/api/buscar-produto", methods=["GET"])
def api_buscar_ean(): # Renomeado para clareza
    if "usuario_id" not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401
        
    ean = request.args.get("ean") # Obter EAN dos query parameters (GET)
    if not ean:
        return jsonify({"error": "Código EAN não fornecido"}), 400

    # 1. Tentar buscar localmente primeiro
    produto_local = buscar_produto_local(ean, session["usuario_id"])
    if produto_local:
        print(f"Produto {ean} encontrado localmente para usuário {session["usuario_id"]}")
        produto_local["source"] = "local_db"
        return jsonify(produto_local)

    # 2. Se não encontrou localmente, buscar na API do Mercado Livre
    print(f"Produto {ean} não encontrado localmente, buscando na API ML...")
    resultado_api = mercado_livre.buscar_produto_por_ean(ean)
    
    if resultado_api and resultado_api.get("success"):
        print(f"Produto {ean} encontrado na API ML: {resultado_api["data"].get("nome")}")
        resultado_api["data"]["source"] = resultado_api.get("source", "api_ml")
        return jsonify(resultado_api["data"])
    else:
        print(f"Produto {ean} não encontrado na API ML. Erro: {resultado_api.get("error")}")
        return jsonify({"error": resultado_api.get("error", "Produto não encontrado"), "ean": ean, "source": resultado_api.get("source", "not_found")}), 404

@app.route("/api/produtos", methods=["POST"])
def api_adicionar_produto(): # Renomeado para clareza
    if "usuario_id" not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401
    
    produto_data = request.json
    usuario_id = session["usuario_id"]
    
    if not produto_data.get("ean") or not produto_data.get("nome") or not produto_data.get("quantidade"):
        return jsonify({"error": "Dados incompletos do produto (EAN, Nome, Quantidade são obrigatórios)"}), 400
        
    try:
        produto_data["quantidade"] = int(produto_data["quantidade"])
        if produto_data["quantidade"] <= 0:
            raise ValueError("Quantidade deve ser positiva")
    except (ValueError, TypeError):
        return jsonify({"error": "Quantidade inválida"}), 400

    produto_data["timestamp"] = datetime.now()
    
    if salvar_produto(produto_data, usuario_id):
        # Retornar a lista atualizada de produtos não enviados
        produtos_atualizados = carregar_produtos_usuario(usuario_id, apenas_nao_enviados=True)
        return jsonify({"success": True, "message": "Produto adicionado/atualizado com sucesso!", "produtos": produtos_atualizados})
    else:
        return jsonify({"error": "Erro ao salvar produto no banco de dados"}), 500

@app.route("/api/enviar-lista", methods=["POST"])
def api_enviar_lista(): # Renomeado para clareza
    if "usuario_id" not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401
        
    usuario_id = session["usuario_id"]
    # Assumindo que o frontend envia JSON para esta API
    data = request.json
    responsavel_id = data.get("responsavel_id")
    pin = data.get("pin")
    
    if not responsavel_id or not pin:
        return jsonify({"error": "ID do Responsável e PIN são obrigatórios"}), 400
        
    try:
        responsavel_id = int(responsavel_id)
    except ValueError:
        return jsonify({"error": "ID do responsável inválido"}), 400

    success, message = enviar_lista_produtos(usuario_id, responsavel_id, pin)
    
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"error": message}), 400 # Usar 400 para erros de lógica/validação

# --- Rotas do Painel Admin ---
@app.route("/admin")
def admin_panel():
    if "usuario_id" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    termo_pesquisa = request.args.get("q", "")
    if termo_pesquisa:
        listas_enviadas = pesquisar_produtos(termo_pesquisa)
    else:
        listas_enviadas = carregar_todas_listas_enviadas()
        
    # Agrupar por usuário para exibição (melhor feito no backend)
    listas_agrupadas = {}
    for produto in listas_enviadas:
        user_key = produto["usuario_id"]
        if user_key not in listas_agrupadas:
            listas_agrupadas[user_key] = {
                "nome_usuario": produto["nome_usuario"],
                "produtos": [],
                # Adicionar info do primeiro produto para data/responsável do envio
                "data_envio": produto["data_envio"],
                "nome_responsavel": produto["nome_responsavel"]
            }
        listas_agrupadas[user_key]["produtos"].append(produto)
        
    # Ordenar listas pela data de envio mais recente (do grupo)
    listas_ordenadas = sorted(listas_agrupadas.values(), key=lambda x: x["data_envio"], reverse=True)
        
    return render_template("admin_panel.html", listas_agrupadas=listas_ordenadas, termo_pesquisa=termo_pesquisa)

@app.route("/api/validar-produtos", methods=["POST"])
def api_validar_produtos(): # Renomeado para clareza
    if "usuario_id" not in session or not session.get("is_admin"):
        return jsonify({"error": "Acesso não autorizado"}), 403
        
    produto_ids = request.json.get("produto_ids")
    validador_id = session["usuario_id"]
    
    if not produto_ids or not isinstance(produto_ids, list):
        return jsonify({"error": "Nenhum ID de produto fornecido"}), 400
        
    try:
        produto_ids_int = [int(pid) for pid in produto_ids]
    except ValueError:
         return jsonify({"error": "IDs de produto inválidos"}), 400

    success, message = validar_lista_produtos(produto_ids_int, validador_id)
    
    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"error": message}), 500 # Usar 500 para erro de DB

@app.route("/exportar_excel")
def exportar_excel():
    if "usuario_id" not in session or not session.get("is_admin"):
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for("index"))
        
    termo_pesquisa = request.args.get("q", "")
    if termo_pesquisa:
        produtos = pesquisar_produtos(termo_pesquisa)
    else:
        produtos = carregar_todas_listas_enviadas()

    if not produtos:
        flash("Não há produtos enviados para exportar.", "warning")
        return redirect(url_for("admin_panel"))

    try:
        produtos_dict = [dict(p) for p in produtos]
        df = pd.DataFrame(produtos_dict)
        colunas_desejadas = {
            "ean": "EAN", "nome": "Descrição", "quantidade": "Quantidade",
            "nome_usuario": "Usuário", "data_envio": "Data Envio", "nome_responsavel": "Responsável Envio",
            "validado": "Validado", "nome_validador": "Validador", "data_validacao": "Data Validação"
        }
        df_export = df[[k for k in colunas_desejadas if k in df.columns]].copy()
        df_export.rename(columns=colunas_desejadas, inplace=True)

        for col in ["Data Envio", "Data Validação"]:
            if col in df_export.columns:
                 df_export[col] = pd.to_datetime(df_export[col], errors='coerce').dt.strftime('%d/%m/%Y %H:%M:%S')
        if "Validado" in df_export.columns:
            df_export["Validado"] = df_export["Validado"].apply(lambda x: "Sim" if x == 1 else "Não")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Produtos")
        output.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"produtos_exportados_{timestamp}.xlsx"
        
        return send_file(
            output, as_attachment=True, download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print(f"Erro ao exportar produtos: {e}")
        flash(f"Erro ao gerar o arquivo Excel: {str(e)}", "danger")
        return redirect(url_for("admin_panel"))

# Inicializar o banco de dados ao iniciar a aplicação
# (Apenas se o ficheiro não existir para evitar recriar sempre)
if not os.path.exists(DATABASE_PATH):
    print(f"Arquivo de banco de dados não encontrado em {DATABASE_PATH}. Inicializando...")
    init_database()
else:
    print("Arquivo de banco de dados encontrado.")
    # Opcional: Poderia verificar a estrutura das tabelas aqui se necessário

if __name__ == "__main__":
    # Usar host=\'0.0.0.0\' para ser acessível na rede local
    # Desativar debug em produção
    # Usar use_reloader=False para evitar a dupla inicialização do DB em modo debug
    app.run(debug=True, host="0.0.0.0", use_reloader=False)


"""
Aplicação principal otimizada do Serv.Local
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.middleware.proxy_fix import ProxyFix

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import active_config
from services.database import db_service
from services.database_init import db_initializer
from services.backup import backup_service
from models.usuario import Usuario
from models.produto import Produto

def create_app():
    """Factory para criar aplicação Flask otimizada"""
    
    # Configurar logging
    setup_logging()
    
    # Criar aplicação
    app = Flask(__name__)
    app.config.from_object(active_config)
    
    # Middleware para proxy (se necessário)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configurar sessões seguras
    app.config.update(
        SESSION_COOKIE_SECURE=False,  # True apenas com HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=active_config.SESSION_TIMEOUT
    )
    
    # Inicializar banco de dados
    if not initialize_database():
        # O erro já foi logado dentro de initialize_database
        # logging.error("Falha na inicialização do banco de dados")
        # Permitir que a aplicação continue mesmo com falha na inicialização/verificação?
        # Por enquanto, vamos manter o comportamento original de sair.
        # Se a aplicação precisar rodar mesmo com DB inicial com erro, comentar a linha abaixo.
        sys.exit(1)
    
    # Inicializar backup automático se habilitado
    if active_config.AUTO_BACKUP:
        backup_service.start_automatic_backup()
    
    # Registrar rotas
    register_routes(app)
    
    # Registrar filtros Jinja2
    register_template_filters(app)
    
    # Handlers de erro
    register_error_handlers(app)
    
    logging.info(f"Aplicação inicializada - Modo: {'DEBUG' if app.debug else 'PRODUÇÃO'}")
    
    return app

def setup_logging():
    """Configura sistema de logging"""
    
    # Garantir que diretório de logs existe
    active_config.init_directories()
    
    # Configurar formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para arquivo
    file_handler = logging.FileHandler(
        active_config.LOGS_DIR / 'app.log',
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, active_config.LOG_LEVEL))
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configurar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, active_config.LOG_LEVEL))
    # Evitar adicionar handlers duplicados se a função for chamada múltiplas vezes
    if not root_logger.hasHandlers():
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Reduzir verbosidade de bibliotecas externas
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def initialize_database():
    """Inicializa banco de dados e verifica saúde de forma mais robusta"""
    try:
        # Tenta inicializar (cria tabelas, insere dados iniciais se necessário)
        success_init = db_initializer.initialize_database()
        if not success_init:
            logging.error("Falha crítica durante a inicialização inicial do banco de dados.")
            return False
        
        # Após inicialização, tenta verificar a saúde
        try:
            health = db_initializer.check_database_health()
            # Verifica se a chave 'status' existe antes de logar
            if 'status' in health:
                status_msg = f"Status: {health['status']}"
                # Verifica se a chave 'tables' existe e se o status não é 'error'
                if health['status'] != 'error' and 'tables' in health:
                    status_msg += f" - Tabelas: {health['tables']}"
                elif 'error' in health:
                    status_msg += f" - Erro na verificação: {health['error']}" # Loga o erro específico da verificação
                logging.info(f"Verificação de saúde do banco concluída. {status_msg}")
            else:
                logging.warning("Resultado da verificação de saúde do banco não contém a chave 'status'.")
                # Mesmo que a verificação falhe ou retorne algo inesperado, 
                # consideramos a inicialização OK se chegou até aqui sem exceções críticas.
                # A aplicação pode funcionar, mas o admin deve verificar os logs.
            
            # Retorna True porque a inicialização base (criação/migração) funcionou.
            # A falha na verificação de saúde é logada, mas não impede o app de iniciar.
            return True 
            
        except Exception as e_check:
            # Captura exceção específica da verificação de saúde
            logging.error(f"Erro durante a verificação de saúde do banco: {e_check}", exc_info=True)
            # Mesmo com erro na verificação, a inicialização pode ter sido bem-sucedida.
            # Retorna True para permitir que a aplicação tente iniciar.
            return True
            
    except Exception as e_init:
        # Captura exceção crítica durante a inicialização inicial
        logging.error(f"Erro CRÍTICO na inicialização do banco: {e_init}", exc_info=True)
        return False

def register_routes(app):
    """Registra todas as rotas da aplicação"""
    
    @app.route('/')
    def index():
        """Página inicial"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = Usuario.find_by_id(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))
        
        # Estatísticas do usuário
        stats = Produto.get_estatisticas(user.id)
        
        return render_template('index.html', user=user, stats=stats)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login de usuário"""
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            senha = request.form.get('senha', '')
            
            if not nome or not senha:
                flash('Nome e senha são obrigatórios', 'error')
                return render_template('login.html')
            
            user = Usuario.find_by_nome(nome)
            if user and user.authenticate(senha):
                session['user_id'] = user.id
                session['user_name'] = user.nome
                session['is_admin'] = bool(user.admin)
                session.permanent = True
                
                logging.info(f"Login bem-sucedido: {nome}")
                return redirect(url_for('index'))
            else:
                flash('Nome ou senha incorretos', 'error')
                logging.warning(f"Tentativa de login falhada: {nome}")
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """Logout de usuário"""
        user_name = session.get('user_name', 'Usuário')
        session.clear()
        logging.info(f"Logout: {user_name}")
        flash('Logout realizado com sucesso', 'success')
        return redirect(url_for('login'))
    
    @app.route('/produtos')
    def produtos():
        """Lista produtos do usuário"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user_id = session['user_id']
        apenas_nao_enviados = request.args.get('pendentes') == '1'
        
        produtos_list = Produto.find_by_usuario(user_id, apenas_nao_enviados)
        
        return render_template('produtos.html', 
                             produtos=produtos_list, 
                             apenas_pendentes=apenas_nao_enviados)
    
    @app.route('/produto/novo', methods=['GET', 'POST'])
    def novo_produto():
        """Cadastro de novo produto"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            try:
                ean = request.form.get('ean', '').strip()
                nome = request.form.get('nome', '').strip()
                quantidade = int(request.form.get('quantidade', 0))
                cor = request.form.get('cor', '').strip() or None
                voltagem = request.form.get('voltagem', '').strip() or None
                modelo = request.form.get('modelo', '').strip() or None
                preco = request.form.get('preco')
                
                if preco:
                    preco = float(preco.replace(',', '.'))
                
                produto = Produto.create_produto(
                    ean=ean,
                    nome=nome,
                    quantidade=quantidade,
                    usuario_id=session['user_id'],
                    cor=cor,
                    voltagem=voltagem,
                    modelo=modelo,
                    preco=preco
                )
                
                if produto:
                    flash('Produto cadastrado com sucesso!', 'success')
                    return redirect(url_for('produtos'))
                else:
                    flash('Erro ao cadastrar produto', 'error')
                    
            except ValueError as e:
                flash(str(e), 'error')
            except Exception as e:
                logging.error(f"Erro ao criar produto: {e}")
                flash('Erro interno do sistema', 'error')
        
        return render_template('novo_produto.html')
    
    @app.route('/api/produto/<int:produto_id>/enviar', methods=['POST'])
    def enviar_produto(produto_id):
        """API para marcar produto como enviado"""
        if 'user_id' not in session:
            return jsonify({'error': 'Não autorizado'}), 401
        
        produto = Produto.find_by_id(produto_id)
        if not produto or produto.usuario_id != session['user_id']:
            return jsonify({'error': 'Produto não encontrado'}), 404
        
        if produto.marcar_como_enviado():
            return jsonify({'success': True, 'message': 'Produto marcado como enviado'})
        else:
            return jsonify({'error': 'Erro ao marcar produto como enviado'}), 500
    
    @app.route('/admin')
    def admin():
        """Painel administrativo"""
        if not session.get('is_admin'):
            flash('Acesso negado', 'error')
            return redirect(url_for('index'))
        
        # Estatísticas gerais
        stats = Produto.get_estatisticas()
        
        # Estatísticas do banco
        db_health = db_initializer.check_database_health()
        
        # Estatísticas de backup
        backup_stats = backup_service.get_stats()
        
        return render_template('admin.html', 
                             stats=stats, 
                             db_health=db_health,
                             backup_stats=backup_stats)
    
    @app.route('/api/backup/create', methods=['POST'])
    def create_backup():
        """API para criar backup manual"""
        if not session.get('is_admin'):
            return jsonify({'error': 'Acesso negado'}), 403
        
        backup_path = backup_service.create_backup()
        if backup_path:
            return jsonify({'success': True, 'backup_path': backup_path})
        else:
            return jsonify({'error': 'Erro ao criar backup'}), 500
    
    @app.route('/api/stats')
    def api_stats():
        """API para estatísticas em tempo real"""
        if 'user_id' not in session:
            return jsonify({'error': 'Não autorizado'}), 401
        
        user_id = session['user_id'] if not session.get('is_admin') else None
        stats = Produto.get_estatisticas(user_id)
        
        return jsonify(stats)

def register_template_filters(app):
    """Registra filtros personalizados para templates"""
    
    @app.template_filter('data_brasileira')
    def data_brasileira_filter(data):
        """Formata data no padrão brasileiro"""
        if not data:
            return ''
        
        try:
            if isinstance(data, str):
                # Tenta converter de ISO format, tratando o 'Z' opcional
                dt = datetime.fromisoformat(data.replace('Z', '+00:00'))
            elif isinstance(data, datetime):
                dt = data
            else:
                 return str(data) # Retorna como string se não for reconhecido
            
            return dt.strftime('%d/%m/%Y %H:%M')
        except Exception as e:
            logging.warning(f"Erro ao formatar data {data}: {e}")
            return str(data)
    
    @app.template_filter('moeda')
    def moeda_filter(valor):
        """Formata valor como moeda brasileira"""
        if valor is None:
            return 'R$ 0,00'
        
        try:
            return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            logging.warning(f"Erro ao formatar moeda {valor}")
            return 'R$ --,--'

def register_error_handlers(app):
    """Registra handlers de erro"""
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message='Página não encontrada'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        # Loga a exceção completa se disponível
        logging.error(f"Erro interno 500: {error}", exc_info=True)
        return render_template('error.html', 
                             error_code=500, 
                             error_message='Erro interno do servidor. Consulte os logs para mais detalhes.'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('error.html', 
                             error_code=403, 
                             error_message='Acesso negado'), 403

def main():
    """Função principal"""
    try:
        app = create_app()
        
        # A mensagem de inicialização agora é mais concisa, 
        # detalhes do banco já foram logados em initialize_database
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    SERV.LOCAL OTIMIZADO v2.0                 ║
║                                                              ║
║  🚀 Iniciando servidor...                                    ║
║  🌐 Acesse: http://{active_config.HOST}:{active_config.PORT}                   ║
║  📝 Logs em: {active_config.LOGS_DIR / 'app.log'}             ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Usar 'waitress' para produção se não estiver em modo debug
        if not active_config.DEBUG:
            try:
                from waitress import serve
                print("    मोडो PRODUÇÃO - Servidor: Waitress")
                serve(app, host=active_config.HOST, port=active_config.PORT, threads=active_config.SERVER_THREADS)
            except ImportError:
                print("   ⚠️  Waitress não instalado. Usando servidor de desenvolvimento Flask.")
                print("      Para produção, instale com: pip install waitress")
                app.run(
                    host=active_config.HOST,
                    port=active_config.PORT,
                    debug=active_config.DEBUG,
                    threaded=True
                )
        else:
            print("    मोडो DEBUG - Servidor: Flask Development")
            app.run(
                host=active_config.HOST,
                port=active_config.PORT,
                debug=active_config.DEBUG,
                threaded=True
            )
            
    except KeyboardInterrupt:
        print("\n🛑 Servidor interrompido pelo usuário")
        logging.info("Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro crítico ao iniciar servidor: {e}")
        logging.error(f"Erro crítico ao iniciar servidor: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()


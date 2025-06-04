"""
Serviço de inicialização e migração do banco de dados
"""
import logging
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash
from services.database import db_service

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Responsável pela inicialização e migração do banco"""
    
    def __init__(self):
        self.version = 1  # Versão atual do schema
    
    def initialize_database(self) -> bool:
        """Inicializa o banco de dados com todas as tabelas e índices"""
        try:
            logger.info("Iniciando inicialização do banco de dados...")
            
            # Criar tabelas
            self._create_tables()
            
            # Criar índices
            self._create_indexes()
            
            # Inserir dados iniciais
            self._insert_initial_data()
            
            # Atualizar versão do schema
            self._update_schema_version()
            
            logger.info("Banco de dados inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco: {e}")
            return False
    
    def _create_tables(self):
        """Cria todas as tabelas do sistema"""
        
        tables = [
            # Tabela de controle de versão do schema
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
            """,
            
            # Tabela de usuários otimizada
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                senha_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                admin INTEGER DEFAULT 0,
                ativo INTEGER DEFAULT 1,
                tentativas_login INTEGER DEFAULT 0,
                bloqueado_ate TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                ultimo_login TEXT
            )
            """,
            
            # Tabela de responsáveis
            """
            CREATE TABLE IF NOT EXISTS responsaveis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                pin TEXT NOT NULL,
                ativo INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
            """,
            
            # Tabela de produtos otimizada
            """
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ean TEXT NOT NULL,
                nome TEXT NOT NULL,
                cor TEXT,
                voltagem TEXT,
                modelo TEXT,
                quantidade INTEGER NOT NULL DEFAULT 0,
                preco REAL,
                usuario_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                enviado INTEGER DEFAULT 0,
                data_envio TEXT,
                validado INTEGER DEFAULT 0,
                validador_id INTEGER,
                data_validacao TEXT,
                responsavel_id INTEGER,
                responsavel_pin TEXT,
                observacoes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
                FOREIGN KEY (validador_id) REFERENCES usuarios (id) ON DELETE SET NULL,
                FOREIGN KEY (responsavel_id) REFERENCES responsaveis (id) ON DELETE SET NULL
            )
            """,
            
            # Tabela de auditoria
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE SET NULL
            )
            """,
            
            # Tabela de sessões
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
            )
            """,
            
            # Tabela de configurações do sistema
            """
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TEXT NOT NULL,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES usuarios (id) ON DELETE SET NULL
            )
            """
        ]
        
        for table_sql in tables:
            db_service.execute_update(table_sql)
            logger.debug(f"Tabela criada/verificada")
    
    def _create_indexes(self):
        """Cria índices otimizados para performance"""
        
        indexes = [
            # Índices para tabela usuarios
            "CREATE INDEX IF NOT EXISTS idx_usuarios_nome ON usuarios(nome)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_admin ON usuarios(admin)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_created_at ON usuarios(created_at)",
            
            # Índices para tabela produtos
            "CREATE INDEX IF NOT EXISTS idx_produtos_ean ON produtos(ean)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos(nome)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_usuario_id ON produtos(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_timestamp ON produtos(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_enviado ON produtos(enviado)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_validado ON produtos(validado)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_data_envio ON produtos(data_envio)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_created_at ON produtos(created_at)",
            
            # Índices compostos para consultas comuns
            "CREATE INDEX IF NOT EXISTS idx_produtos_usuario_enviado ON produtos(usuario_id, enviado)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_ean_usuario ON produtos(ean, usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_enviado_data ON produtos(enviado, data_envio)",
            "CREATE INDEX IF NOT EXISTS idx_produtos_validado_data ON produtos(validado, data_validacao)",
            
            # Índices para tabela responsaveis
            "CREATE INDEX IF NOT EXISTS idx_responsaveis_nome ON responsaveis(nome)",
            "CREATE INDEX IF NOT EXISTS idx_responsaveis_ativo ON responsaveis(ativo)",
            
            # Índices para tabela audit_log
            "CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_table_record ON audit_log(table_name, record_id)",
            
            # Índices para tabela user_sessions
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON user_sessions(last_activity)",
            
            # Índices para tabela system_config
            "CREATE INDEX IF NOT EXISTS idx_config_updated_at ON system_config(updated_at)"
        ]
        
        for index_sql in indexes:
            db_service.execute_update(index_sql)
            logger.debug(f"Índice criado/verificado")
    
    def _insert_initial_data(self):
        """Insere dados iniciais necessários"""
        
        # Verificar se já existe usuário admin
        admin_exists = db_service.execute_query(
            "SELECT COUNT(*) as count FROM usuarios WHERE admin = 1"
        )
        
        if admin_exists[0]['count'] == 0:
            # Criar usuário admin padrão
            admin_hash = generate_password_hash("admin123")  # Senha mais segura
            salt = "admin_salt_default"
            now = datetime.now().isoformat()
            
            db_service.execute_insert(
                """INSERT INTO usuarios 
                   (nome, senha_hash, salt, admin, created_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                ("admin", admin_hash, salt, 1, now)
            )
            logger.info("Usuário admin criado com senha padrão")
        
        # Inserir responsáveis padrão se não existirem
        responsaveis_count = db_service.execute_query(
            "SELECT COUNT(*) as count FROM responsaveis"
        )
        
        if responsaveis_count[0]['count'] == 0:
            responsaveis = [
                ("Liliane", "5584"),
                ("Rogerio", "9841"),
                ("Celso", "2122"),
                ("Marcos", "6231")
            ]
            
            now = datetime.now().isoformat()
            for nome, pin in responsaveis:
                db_service.execute_insert(
                    """INSERT INTO responsaveis (nome, pin, created_at) 
                       VALUES (?, ?, ?)""",
                    (nome, pin, now)
                )
            
            logger.info(f"Inseridos {len(responsaveis)} responsáveis padrão")
        
        # Inserir configurações padrão do sistema
        configs = [
            ("app_name", "Serv.Local Otimizado", "Nome da aplicação"),
            ("app_version", "2.0.0", "Versão da aplicação"),
            ("backup_enabled", "true", "Backup automático habilitado"),
            ("session_timeout", "3600", "Timeout de sessão em segundos"),
            ("max_login_attempts", "5", "Máximo de tentativas de login"),
            ("lockout_duration", "900", "Duração do bloqueio em segundos")
        ]
        
        now = datetime.now().isoformat()
        for key, value, description in configs:
            # Verificar se já existe
            existing = db_service.execute_query(
                "SELECT COUNT(*) as count FROM system_config WHERE key = ?",
                (key,)
            )
            
            if existing[0]['count'] == 0:
                db_service.execute_insert(
                    """INSERT INTO system_config (key, value, description, updated_at) 
                       VALUES (?, ?, ?, ?)""",
                    (key, value, description, now)
                )
        
        logger.info("Configurações padrão inseridas")
    
    def _update_schema_version(self):
        """Atualiza a versão do schema"""
        now = datetime.now().isoformat()
        
        # Verificar versão atual
        current_version = db_service.execute_query(
            "SELECT MAX(version) as version FROM schema_version"
        )
        
        if not current_version or current_version[0]['version'] is None:
            # Primeira inicialização
            db_service.execute_insert(
                """INSERT INTO schema_version (version, applied_at, description) 
                   VALUES (?, ?, ?)""",
                (self.version, now, "Inicialização do banco otimizado")
            )
            logger.info(f"Schema versão {self.version} aplicada")
    
    def check_database_health(self) -> dict:
        """Verifica a saúde do banco de dados"""
        try:
            # Verificar integridade
            integrity = db_service.execute_query("PRAGMA integrity_check")
            
            # Estatísticas das tabelas
            stats = {}
            tables = ['usuarios', 'produtos', 'responsaveis', 'audit_log']
            
            for table in tables:
                count = db_service.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = count[0]['count']
            
            # Tamanho do banco
            size_info = db_service.execute_query("PRAGMA page_count, page_size")
            if size_info:
                page_count = size_info[0][0]
                page_size = size_info[0][1]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
            else:
                db_size_mb = 0
            
            return {
                'status': 'healthy' if integrity[0][0] == 'ok' else 'corrupted',
                'integrity': integrity[0][0],
                'tables': stats,
                'size_mb': round(db_size_mb, 2),
                'pool_stats': db_service.get_stats()
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar saúde do banco: {e}")
            return {'status': 'error', 'error': str(e)}

# Instância global
db_initializer = DatabaseInitializer()


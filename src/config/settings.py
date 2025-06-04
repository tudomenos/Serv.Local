"""
Configurações centralizadas do sistema Serv.Local Otimizado
"""
import os
import secrets
from pathlib import Path

class Config:
    """Configurações base do sistema"""
    
    # Diretórios base
    BASE_DIR = Path(__file__).parent.parent.parent
    SRC_DIR = BASE_DIR / 'src'
    DATA_DIR = BASE_DIR / 'data'
    BACKUP_DIR = BASE_DIR / 'backups'
    LOGS_DIR = BASE_DIR / 'logs'
    
    # Configurações de aplicação
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    
    # Configurações de banco de dados
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or str(DATA_DIR / 'produtos.db')
    DATABASE_BACKUP_PATH = os.environ.get('BACKUP_PATH') or str(BACKUP_DIR)
    
    # Configurações de segurança
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', 3600))  # 1 hora
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 8))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION', 900))  # 15 minutos
    
    # Configurações de performance
    CONNECTION_POOL_SIZE = int(os.environ.get('POOL_SIZE', 10))
    CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))  # 5 minutos
    
    # Configurações de API externa
    MERCADO_LIVRE_CLIENT_ID = os.environ.get('ML_CLIENT_ID', '')
    MERCADO_LIVRE_CLIENT_SECRET = os.environ.get('ML_CLIENT_SECRET', '')
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 30))
    
    # Configurações de backup
    AUTO_BACKUP = os.environ.get('AUTO_BACKUP', 'True').lower() == 'true'
    BACKUP_INTERVAL = int(os.environ.get('BACKUP_INTERVAL', 3600))  # 1 hora
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', 30))
    
    # Configurações de logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    @classmethod
    def init_directories(cls):
        """Cria diretórios necessários se não existirem"""
        for directory in [cls.DATA_DIR, cls.BACKUP_DIR, cls.LOGS_DIR]:
            directory.mkdir(exist_ok=True)

class LocalConfig(Config):
    """Configurações específicas para ambiente local"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Configurações para ambiente de produção local"""
    DEBUG = False
    LOG_LEVEL = 'INFO'

# Configuração ativa baseada na variável de ambiente
config_name = os.environ.get('FLASK_ENV', 'local')
if config_name == 'production':
    active_config = ProductionConfig
else:
    active_config = LocalConfig


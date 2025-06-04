"""
Modelo de usuário otimizado com segurança melhorada
"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from models.base import BaseModel
from services.database import db_service
import logging

logger = logging.getLogger(__name__)

class Usuario(BaseModel):
    """Modelo de usuário com funcionalidades de segurança"""
    
    table_name = "usuarios"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nome = kwargs.get('nome', '')
        self.email = kwargs.get('email')
        self.senha_hash = kwargs.get('senha_hash', '')
        self.salt = kwargs.get('salt', '')
        self.admin = kwargs.get('admin', 0)
        self.ativo = kwargs.get('ativo', 1)
        self.tentativas_login = kwargs.get('tentativas_login', 0)
        self.bloqueado_ate = kwargs.get('bloqueado_ate')
        self.ultimo_login = kwargs.get('ultimo_login')
    
    @classmethod
    def find_by_nome(cls, nome: str) -> Optional['Usuario']:
        """Busca usuário por nome"""
        try:
            result = db_service.execute_query(
                "SELECT * FROM usuarios WHERE nome = ? AND ativo = 1",
                (nome,)
            )
            if result:
                return cls(**dict(result[0]))
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por nome {nome}: {e}")
            return None
    
    @classmethod
    def find_by_email(cls, email: str) -> Optional['Usuario']:
        """Busca usuário por email"""
        try:
            result = db_service.execute_query(
                "SELECT * FROM usuarios WHERE email = ? AND ativo = 1",
                (email,)
            )
            if result:
                return cls(**dict(result[0]))
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar usuário por email {email}: {e}")
            return None
    
    @classmethod
    def create_user(cls, nome: str, senha: str, email: str = None, admin: bool = False) -> Optional['Usuario']:
        """Cria novo usuário com validações de segurança"""
        
        # Validar dados
        if not cls._validate_username(nome):
            raise ValueError("Nome de usuário inválido")
        
        if not cls._validate_password(senha):
            raise ValueError("Senha não atende aos critérios de segurança")
        
        if email and not cls._validate_email(email):
            raise ValueError("Email inválido")
        
        # Verificar se usuário já existe
        if cls.find_by_nome(nome):
            raise ValueError("Nome de usuário já existe")
        
        if email and cls.find_by_email(email):
            raise ValueError("Email já está em uso")
        
        try:
            # Gerar hash da senha com salt
            salt = secrets.token_hex(16)
            senha_hash = generate_password_hash(senha + salt)
            
            now = datetime.now().isoformat()
            
            user_id = db_service.execute_insert(
                """INSERT INTO usuarios 
                   (nome, email, senha_hash, salt, admin, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nome, email, senha_hash, salt, int(admin), now, now)
            )
            
            if user_id:
                logger.info(f"Usuário criado: {nome} (ID: {user_id})")
                return cls.find_by_id(user_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário {nome}: {e}")
            raise
    
    def authenticate(self, senha: str) -> bool:
        """Autentica usuário com controle de tentativas"""
        
        # Verificar se conta está bloqueada
        if self.is_locked():
            logger.warning(f"Tentativa de login em conta bloqueada: {self.nome}")
            return False
        
        # Verificar senha
        if check_password_hash(self.senha_hash, senha + self.salt):
            # Login bem-sucedido
            self._reset_login_attempts()
            self._update_last_login()
            logger.info(f"Login bem-sucedido: {self.nome}")
            return True
        else:
            # Login falhou
            self._increment_login_attempts()
            logger.warning(f"Tentativa de login falhada: {self.nome}")
            return False
    
    def is_locked(self) -> bool:
        """Verifica se conta está bloqueada"""
        if not self.bloqueado_ate:
            return False
        
        try:
            bloqueio_ate = datetime.fromisoformat(self.bloqueado_ate)
            if datetime.now() > bloqueio_ate:
                # Bloqueio expirou, limpar
                self._unlock_account()
                return False
            return True
        except:
            return False
    
    def change_password(self, senha_atual: str, nova_senha: str) -> bool:
        """Altera senha do usuário"""
        
        # Verificar senha atual
        if not check_password_hash(self.senha_hash, senha_atual + self.salt):
            return False
        
        # Validar nova senha
        if not self._validate_password(nova_senha):
            raise ValueError("Nova senha não atende aos critérios de segurança")
        
        try:
            # Gerar novo salt e hash
            self.salt = secrets.token_hex(16)
            self.senha_hash = generate_password_hash(nova_senha + self.salt)
            self.updated_at = datetime.now().isoformat()
            
            return self._update()
            
        except Exception as e:
            logger.error(f"Erro ao alterar senha do usuário {self.nome}: {e}")
            return False
    
    def _increment_login_attempts(self):
        """Incrementa tentativas de login e bloqueia se necessário"""
        self.tentativas_login += 1
        
        # Bloquear após 5 tentativas
        if self.tentativas_login >= 5:
            bloqueio_ate = datetime.now() + timedelta(minutes=15)
            self.bloqueado_ate = bloqueio_ate.isoformat()
            logger.warning(f"Conta bloqueada por tentativas excessivas: {self.nome}")
        
        self.updated_at = datetime.now().isoformat()
        self._update()
    
    def _reset_login_attempts(self):
        """Reseta tentativas de login"""
        self.tentativas_login = 0
        self.bloqueado_ate = None
        self.updated_at = datetime.now().isoformat()
        self._update()
    
    def _unlock_account(self):
        """Desbloqueia conta"""
        self.tentativas_login = 0
        self.bloqueado_ate = None
        self.updated_at = datetime.now().isoformat()
        self._update()
    
    def _update_last_login(self):
        """Atualiza último login"""
        self.ultimo_login = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self._update()
    
    @staticmethod
    def _validate_username(nome: str) -> bool:
        """Valida nome de usuário"""
        if not nome or len(nome) < 3:
            return False
        if len(nome) > 50:
            return False
        # Apenas letras, números e underscore
        return nome.replace('_', '').replace('-', '').isalnum()
    
    @staticmethod
    def _validate_password(senha: str) -> bool:
        """Valida força da senha"""
        if len(senha) < 8:
            return False
        if len(senha) > 128:
            return False
        
        # Verificar complexidade
        has_upper = any(c.isupper() for c in senha)
        has_lower = any(c.islower() for c in senha)
        has_digit = any(c.isdigit() for c in senha)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in senha)
        
        return sum([has_upper, has_lower, has_digit, has_special]) >= 3
    
    @staticmethod
    def _validate_email(email: str) -> bool:
        """Valida formato de email"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _insert(self) -> bool:
        """Insere novo usuário"""
        try:
            self.id = db_service.execute_insert(
                """INSERT INTO usuarios 
                   (nome, email, senha_hash, salt, admin, ativo, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.nome, self.email, self.senha_hash, self.salt, 
                 self.admin, self.ativo, self.created_at, self.updated_at)
            )
            return self.id is not None
        except Exception as e:
            logger.error(f"Erro ao inserir usuário: {e}")
            return False
    
    def _update(self) -> bool:
        """Atualiza usuário existente"""
        try:
            affected = db_service.execute_update(
                """UPDATE usuarios SET 
                   nome = ?, email = ?, senha_hash = ?, salt = ?, 
                   admin = ?, ativo = ?, tentativas_login = ?, 
                   bloqueado_ate = ?, ultimo_login = ?, updated_at = ?
                   WHERE id = ?""",
                (self.nome, self.email, self.senha_hash, self.salt,
                 self.admin, self.ativo, self.tentativas_login,
                 self.bloqueado_ate, self.ultimo_login, self.updated_at, self.id)
            )
            return affected > 0
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário {self.id}: {e}")
            return False
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Converte para dicionário, excluindo dados sensíveis por padrão"""
        data = super().to_dict()
        
        if not include_sensitive:
            # Remover dados sensíveis
            data.pop('senha_hash', None)
            data.pop('salt', None)
        
        return data


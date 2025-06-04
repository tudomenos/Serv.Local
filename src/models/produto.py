"""
Modelo de produto otimizado com cache e validações
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from models.base import BaseModel
from services.database import db_service
import logging

logger = logging.getLogger(__name__)

class Produto(BaseModel):
    """Modelo de produto com funcionalidades otimizadas"""
    
    table_name = "produtos"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ean = kwargs.get('ean', '')
        self.nome = kwargs.get('nome', '')
        self.cor = kwargs.get('cor')
        self.voltagem = kwargs.get('voltagem')
        self.modelo = kwargs.get('modelo')
        self.quantidade = kwargs.get('quantidade', 0)
        self.preco = kwargs.get('preco')
        self.usuario_id = kwargs.get('usuario_id')
        self.timestamp = kwargs.get('timestamp')
        self.enviado = kwargs.get('enviado', 0)
        self.data_envio = kwargs.get('data_envio')
        self.validado = kwargs.get('validado', 0)
        self.validador_id = kwargs.get('validador_id')
        self.data_validacao = kwargs.get('data_validacao')
        self.responsavel_id = kwargs.get('responsavel_id')
        self.responsavel_pin = kwargs.get('responsavel_pin')
        self.observacoes = kwargs.get('observacoes')
    
    @classmethod
    def find_by_ean(cls, ean: str, usuario_id: int = None) -> List['Produto']:
        """Busca produtos por EAN"""
        try:
            if usuario_id:
                result = db_service.execute_query(
                    "SELECT * FROM produtos WHERE ean = ? AND usuario_id = ? ORDER BY created_at DESC",
                    (ean, usuario_id)
                )
            else:
                result = db_service.execute_query(
                    "SELECT * FROM produtos WHERE ean = ? ORDER BY created_at DESC",
                    (ean,)
                )
            return [cls(**dict(row)) for row in result]
        except Exception as e:
            logger.error(f"Erro ao buscar produtos por EAN {ean}: {e}")
            return []
    
    @classmethod
    def find_by_usuario(cls, usuario_id: int, apenas_nao_enviados: bool = False) -> List['Produto']:
        """Busca produtos por usuário"""
        try:
            if apenas_nao_enviados:
                result = db_service.execute_query(
                    "SELECT * FROM produtos WHERE usuario_id = ? AND enviado = 0 ORDER BY created_at DESC",
                    (usuario_id,)
                )
            else:
                result = db_service.execute_query(
                    "SELECT * FROM produtos WHERE usuario_id = ? ORDER BY created_at DESC",
                    (usuario_id,)
                )
            return [cls(**dict(row)) for row in result]
        except Exception as e:
            logger.error(f"Erro ao buscar produtos do usuário {usuario_id}: {e}")
            return []
    
    @classmethod
    def find_enviados(cls, validados_apenas: bool = False) -> List['Produto']:
        """Busca produtos enviados"""
        try:
            if validados_apenas:
                query = """
                    SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador, r.nome as nome_responsavel
                    FROM produtos p
                    LEFT JOIN usuarios u ON p.usuario_id = u.id
                    LEFT JOIN usuarios v ON p.validador_id = v.id
                    LEFT JOIN responsaveis r ON p.responsavel_id = r.id
                    WHERE p.enviado = 1 AND p.validado = 1
                    ORDER BY p.data_validacao DESC
                """
            else:
                query = """
                    SELECT p.*, u.nome as nome_usuario, v.nome as nome_validador, r.nome as nome_responsavel
                    FROM produtos p
                    LEFT JOIN usuarios u ON p.usuario_id = u.id
                    LEFT JOIN usuarios v ON p.validador_id = v.id
                    LEFT JOIN responsaveis r ON p.responsavel_id = r.id
                    WHERE p.enviado = 1
                    ORDER BY p.data_envio DESC
                """
            
            result = db_service.execute_query(query)
            produtos = []
            for row in result:
                produto = cls(**dict(row))
                # Adicionar nomes relacionados
                produto.nome_usuario = row.get('nome_usuario')
                produto.nome_validador = row.get('nome_validador')
                produto.nome_responsavel = row.get('nome_responsavel')
                produtos.append(produto)
            
            return produtos
        except Exception as e:
            logger.error(f"Erro ao buscar produtos enviados: {e}")
            return []
    
    @classmethod
    def create_produto(cls, ean: str, nome: str, quantidade: int, usuario_id: int, **kwargs) -> Optional['Produto']:
        """Cria novo produto com validações"""
        
        # Validar dados obrigatórios
        if not cls._validate_ean(ean):
            raise ValueError("EAN inválido")
        
        if not nome or len(nome.strip()) < 2:
            raise ValueError("Nome do produto deve ter pelo menos 2 caracteres")
        
        if quantidade < 0:
            raise ValueError("Quantidade não pode ser negativa")
        
        if not usuario_id:
            raise ValueError("Usuário é obrigatório")
        
        try:
            now = datetime.now().isoformat()
            
            produto = cls(
                ean=ean.strip(),
                nome=nome.strip(),
                quantidade=quantidade,
                usuario_id=usuario_id,
                timestamp=now,
                created_at=now,
                updated_at=now,
                **kwargs
            )
            
            if produto.save():
                logger.info(f"Produto criado: {ean} - {nome} (ID: {produto.id})")
                return produto
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao criar produto {ean}: {e}")
            raise
    
    def marcar_como_enviado(self, responsavel_id: int = None, responsavel_pin: str = None) -> bool:
        """Marca produto como enviado"""
        try:
            self.enviado = 1
            self.data_envio = datetime.now().isoformat()
            self.responsavel_id = responsavel_id
            self.responsavel_pin = responsavel_pin
            self.updated_at = datetime.now().isoformat()
            
            success = self._update()
            if success:
                logger.info(f"Produto {self.id} marcado como enviado")
            return success
            
        except Exception as e:
            logger.error(f"Erro ao marcar produto {self.id} como enviado: {e}")
            return False
    
    def validar_produto(self, validador_id: int, observacoes: str = None) -> bool:
        """Valida produto enviado"""
        try:
            self.validado = 1
            self.validador_id = validador_id
            self.data_validacao = datetime.now().isoformat()
            if observacoes:
                self.observacoes = observacoes
            self.updated_at = datetime.now().isoformat()
            
            success = self._update()
            if success:
                logger.info(f"Produto {self.id} validado por usuário {validador_id}")
            return success
            
        except Exception as e:
            logger.error(f"Erro ao validar produto {self.id}: {e}")
            return False
    
    def atualizar_quantidade(self, nova_quantidade: int) -> bool:
        """Atualiza quantidade do produto"""
        if nova_quantidade < 0:
            raise ValueError("Quantidade não pode ser negativa")
        
        try:
            self.quantidade = nova_quantidade
            self.updated_at = datetime.now().isoformat()
            
            success = self._update()
            if success:
                logger.info(f"Quantidade do produto {self.id} atualizada para {nova_quantidade}")
            return success
            
        except Exception as e:
            logger.error(f"Erro ao atualizar quantidade do produto {self.id}: {e}")
            return False
    
    @staticmethod
    def _validate_ean(ean: str) -> bool:
        """Valida formato do EAN"""
        if not ean:
            return False
        
        # Remover espaços e caracteres especiais
        ean_clean = ''.join(c for c in ean if c.isdigit())
        
        # EAN deve ter 8, 12, 13 ou 14 dígitos
        return len(ean_clean) in [8, 12, 13, 14]
    
    def _insert(self) -> bool:
        """Insere novo produto"""
        try:
            self.id = db_service.execute_insert(
                """INSERT INTO produtos 
                   (ean, nome, cor, voltagem, modelo, quantidade, preco, usuario_id, 
                    timestamp, enviado, data_envio, validado, validador_id, data_validacao,
                    responsavel_id, responsavel_pin, observacoes, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.ean, self.nome, self.cor, self.voltagem, self.modelo, 
                 self.quantidade, self.preco, self.usuario_id, self.timestamp,
                 self.enviado, self.data_envio, self.validado, self.validador_id,
                 self.data_validacao, self.responsavel_id, self.responsavel_pin,
                 self.observacoes, self.created_at, self.updated_at)
            )
            return self.id is not None
        except Exception as e:
            logger.error(f"Erro ao inserir produto: {e}")
            return False
    
    def _update(self) -> bool:
        """Atualiza produto existente"""
        try:
            affected = db_service.execute_update(
                """UPDATE produtos SET 
                   ean = ?, nome = ?, cor = ?, voltagem = ?, modelo = ?, 
                   quantidade = ?, preco = ?, timestamp = ?, enviado = ?, 
                   data_envio = ?, validado = ?, validador_id = ?, data_validacao = ?,
                   responsavel_id = ?, responsavel_pin = ?, observacoes = ?, updated_at = ?
                   WHERE id = ?""",
                (self.ean, self.nome, self.cor, self.voltagem, self.modelo,
                 self.quantidade, self.preco, self.timestamp, self.enviado,
                 self.data_envio, self.validado, self.validador_id, self.data_validacao,
                 self.responsavel_id, self.responsavel_pin, self.observacoes,
                 self.updated_at, self.id)
            )
            return affected > 0
        except Exception as e:
            logger.error(f"Erro ao atualizar produto {self.id}: {e}")
            return False
    
    @classmethod
    def get_estatisticas(cls, usuario_id: int = None) -> Dict[str, Any]:
        """Retorna estatísticas dos produtos"""
        try:
            if usuario_id:
                where_clause = "WHERE usuario_id = ?"
                params = (usuario_id,)
            else:
                where_clause = ""
                params = None
            
            # Contadores básicos
            total = cls.count(where_clause.replace("WHERE ", ""), params)
            enviados = cls.count(f"{where_clause} {'AND' if where_clause else 'WHERE'} enviado = 1", 
                               params + (1,) if params else (1,))
            validados = cls.count(f"{where_clause} {'AND' if where_clause else 'WHERE'} validado = 1", 
                                params + (1,) if params else (1,))
            
            # Quantidade total
            query = f"SELECT SUM(quantidade) as total_quantidade FROM produtos {where_clause}"
            result = db_service.execute_query(query, params)
            total_quantidade = result[0]['total_quantidade'] if result and result[0]['total_quantidade'] else 0
            
            return {
                'total_produtos': total,
                'produtos_enviados': enviados,
                'produtos_validados': validados,
                'produtos_pendentes': total - enviados,
                'total_quantidade': total_quantidade,
                'taxa_envio': round((enviados / max(1, total)) * 100, 2),
                'taxa_validacao': round((validados / max(1, enviados)) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}


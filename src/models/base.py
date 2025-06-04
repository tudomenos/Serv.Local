"""
Modelo base com funcionalidades comuns
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from services.database import db_service

logger = logging.getLogger(__name__)

class BaseModel:
    """Classe base para todos os modelos"""
    
    table_name = None
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
    
    @classmethod
    def find_by_id(cls, id: int) -> Optional['BaseModel']:
        """Busca registro por ID"""
        try:
            result = db_service.execute_query(
                f"SELECT * FROM {cls.table_name} WHERE id = ?",
                (id,)
            )
            if result:
                return cls(**dict(result[0]))
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar {cls.__name__} por ID {id}: {e}")
            return None
    
    @classmethod
    def find_all(cls, where_clause: str = "", params: tuple = None) -> List['BaseModel']:
        """Busca todos os registros com filtro opcional"""
        try:
            query = f"SELECT * FROM {cls.table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            result = db_service.execute_query(query, params)
            return [cls(**dict(row)) for row in result]
        except Exception as e:
            logger.error(f"Erro ao buscar {cls.__name__}: {e}")
            return []
    
    @classmethod
    def count(cls, where_clause: str = "", params: tuple = None) -> int:
        """Conta registros com filtro opcional"""
        try:
            query = f"SELECT COUNT(*) as count FROM {cls.table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            
            result = db_service.execute_query(query, params)
            return result[0]['count'] if result else 0
        except Exception as e:
            logger.error(f"Erro ao contar {cls.__name__}: {e}")
            return 0
    
    def save(self) -> bool:
        """Salva o modelo (insert ou update)"""
        try:
            now = datetime.now().isoformat()
            
            if self.id:
                # Update
                self.updated_at = now
                return self._update()
            else:
                # Insert
                self.created_at = now
                self.updated_at = now
                return self._insert()
        except Exception as e:
            logger.error(f"Erro ao salvar {self.__class__.__name__}: {e}")
            return False
    
    def delete(self) -> bool:
        """Remove o registro"""
        if not self.id:
            return False
        
        try:
            affected = db_service.execute_update(
                f"DELETE FROM {self.table_name} WHERE id = ?",
                (self.id,)
            )
            return affected > 0
        except Exception as e:
            logger.error(f"Erro ao deletar {self.__class__.__name__} {self.id}: {e}")
            return False
    
    def _insert(self) -> bool:
        """Implementar nas classes filhas"""
        raise NotImplementedError
    
    def _update(self) -> bool:
        """Implementar nas classes filhas"""
        raise NotImplementedError
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte modelo para dicionário"""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }


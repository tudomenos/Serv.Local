"""
Serviço de banco de dados otimizado com pool de conexões
"""
import sqlite3
import threading
import time
import logging
from queue import Queue, Empty
from contextlib import contextmanager
from typing import Optional, Any, Dict, List
from config.settings import active_config

logger = logging.getLogger(__name__)

class ConnectionPool:
    """Pool de conexões SQLite otimizado para ambiente local"""
    
    def __init__(self, database_path: str, pool_size: int = 10):
        self.database_path = database_path
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.stats = {
            'connections_created': 0,
            'connections_reused': 0,
            'pool_hits': 0,
            'pool_misses': 0
        }
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Inicializa o pool com conexões"""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            if conn:
                self.pool.put(conn)
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Cria uma nova conexão SQLite otimizada"""
        try:
            conn = sqlite3.connect(
                self.database_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False,
                timeout=30.0
            )
            
            # Configurações de otimização
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")  # Melhora concorrência
            conn.execute("PRAGMA synchronous = NORMAL")  # Balance entre segurança e performance
            conn.execute("PRAGMA cache_size = 10000")  # Cache de 10MB
            conn.execute("PRAGMA temp_store = MEMORY")  # Tabelas temporárias em memória
            conn.execute("PRAGMA mmap_size = 268435456")  # Memory-mapped I/O de 256MB
            
            self.stats['connections_created'] += 1
            logger.debug(f"Nova conexão criada. Total: {self.stats['connections_created']}")
            return conn
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar conexão: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """Context manager para obter conexão do pool"""
        conn = None
        from_pool = False
        
        try:
            # Tentar obter conexão do pool
            try:
                conn = self.pool.get(timeout=5)
                from_pool = True
                self.stats['pool_hits'] += 1
                logger.debug("Conexão obtida do pool")
            except Empty:
                # Pool vazio, criar conexão temporária
                conn = self._create_connection()
                self.stats['pool_misses'] += 1
                logger.debug("Pool vazio, criando conexão temporária")
            
            if not conn:
                raise sqlite3.Error("Não foi possível obter conexão")
            
            # Verificar se conexão ainda está válida
            try:
                conn.execute("SELECT 1")
                yield conn
            except sqlite3.Error:
                # Conexão inválida, criar nova
                if from_pool:
                    conn.close()
                conn = self._create_connection()
                if conn:
                    yield conn
                else:
                    raise sqlite3.Error("Falha ao recriar conexão")
                    
        except Exception as e:
            logger.error(f"Erro no pool de conexões: {e}")
            raise
        finally:
            if conn:
                if from_pool:
                    # Retornar ao pool se veio de lá
                    try:
                        self.pool.put(conn, timeout=1)
                        self.stats['connections_reused'] += 1
                    except:
                        # Pool cheio, fechar conexão
                        conn.close()
                else:
                    # Conexão temporária, fechar
                    conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do pool"""
        return {
            **self.stats,
            'pool_size': self.pool_size,
            'current_pool_size': self.pool.qsize(),
            'hit_rate': self.stats['pool_hits'] / max(1, self.stats['pool_hits'] + self.stats['pool_misses'])
        }
    
    def close_all(self):
        """Fecha todas as conexões do pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break

class DatabaseService:
    """Serviço principal de banco de dados"""
    
    def __init__(self):
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Inicializa o pool de conexões"""
        try:
            # Garantir que diretórios existem
            active_config.init_directories()
            
            self.pool = ConnectionPool(
                active_config.DATABASE_PATH,
                active_config.CONNECTION_POOL_SIZE
            )
            logger.info(f"Pool de conexões inicializado: {active_config.DATABASE_PATH}")
        except Exception as e:
            logger.error(f"Erro ao inicializar pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Obtém conexão do pool"""
        if not self.pool:
            self._initialize_pool()
        
        with self.pool.get_connection() as conn:
            yield conn
    
    def execute_query(self, query: str, params: tuple = None) -> List[sqlite3.Row]:
        """Executa query SELECT e retorna resultados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """Executa query UPDATE/INSERT/DELETE e retorna linhas afetadas"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """Executa INSERT e retorna ID do registro inserido"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.lastrowid
    
    def execute_transaction(self, operations: List[tuple]) -> bool:
        """Executa múltiplas operações em uma transação"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for query, params in operations:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Erro na transação: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do banco"""
        if self.pool:
            return self.pool.get_stats()
        return {}
    
    def close(self):
        """Fecha o serviço de banco"""
        if self.pool:
            self.pool.close_all()

# Instância global do serviço
db_service = DatabaseService()


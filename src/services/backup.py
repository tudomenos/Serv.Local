"""
Serviço de backup automático otimizado para ambiente local
"""
import os
import shutil
import sqlite3
import schedule
import time
import threading
import zipfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.settings import active_config

logger = logging.getLogger(__name__)

class BackupService:
    """Serviço de backup automático com compressão e limpeza"""
    
    def __init__(self):
        self.backup_dir = Path(active_config.BACKUP_DIR)
        self.database_path = Path(active_config.DATABASE_PATH)
        self.running = False
        self.thread = None
        self.stats = {
            'backups_created': 0,
            'backups_failed': 0,
            'last_backup': None,
            'last_error': None,
            'total_size_mb': 0
        }
        
        # Garantir que diretório de backup existe
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Serviço de backup inicializado: {self.backup_dir}")
    
    def create_backup(self, backup_name: str = None, compress: bool = True) -> Optional[str]:
        """Cria backup do banco de dados"""
        try:
            if not backup_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"backup_{timestamp}"
            
            # Arquivo de backup temporário
            temp_backup = self.backup_dir / f"{backup_name}.db"
            
            # Usar backup online do SQLite para consistência
            logger.info(f"Iniciando backup: {backup_name}")
            
            with sqlite3.connect(str(self.database_path)) as source:
                with sqlite3.connect(str(temp_backup)) as backup_conn:
                    source.backup(backup_conn)
            
            final_backup_path = temp_backup
            
            # Comprimir se solicitado
            if compress:
                zip_path = self.backup_dir / f"{backup_name}.zip"
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                    zipf.write(temp_backup, temp_backup.name)
                    
                    # Adicionar metadados
                    metadata = {
                        'created_at': datetime.now().isoformat(),
                        'database_path': str(self.database_path),
                        'original_size': temp_backup.stat().st_size,
                        'version': '2.0.0'
                    }
                    
                    import json
                    zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
                
                # Remover arquivo temporário
                temp_backup.unlink()
                final_backup_path = zip_path
            
            # Atualizar estatísticas
            file_size_mb = final_backup_path.stat().st_size / (1024 * 1024)
            self.stats['backups_created'] += 1
            self.stats['last_backup'] = datetime.now().isoformat()
            self.stats['total_size_mb'] += file_size_mb
            
            logger.info(f"Backup criado com sucesso: {final_backup_path} ({file_size_mb:.2f} MB)")
            return str(final_backup_path)
            
        except Exception as e:
            self.stats['backups_failed'] += 1
            self.stats['last_error'] = str(e)
            logger.error(f"Erro ao criar backup: {e}")
            return None
    
    def restore_backup(self, backup_file: str, create_pre_restore_backup: bool = True) -> bool:
        """Restaura backup com segurança"""
        try:
            backup_path = Path(backup_file)
            
            if not backup_path.exists():
                raise FileNotFoundError(f"Arquivo de backup não encontrado: {backup_file}")
            
            # Criar backup de segurança antes de restaurar
            if create_pre_restore_backup:
                pre_restore_backup = self.create_backup("pre_restore_backup", compress=True)
                if not pre_restore_backup:
                    raise Exception("Falha ao criar backup de segurança")
                logger.info(f"Backup de segurança criado: {pre_restore_backup}")
            
            # Extrair arquivo se for ZIP
            if backup_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    # Verificar se contém arquivo .db
                    db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                    if not db_files:
                        raise Exception("Arquivo ZIP não contém banco de dados válido")
                    
                    # Extrair para diretório temporário
                    temp_dir = self.backup_dir / 'temp_restore'
                    temp_dir.mkdir(exist_ok=True)
                    
                    zipf.extract(db_files[0], temp_dir)
                    extracted_file = temp_dir / db_files[0]
            else:
                extracted_file = backup_path
            
            # Verificar integridade do backup
            if not self._verify_backup_integrity(extracted_file):
                raise Exception("Backup corrompido ou inválido")
            
            # Fazer backup do arquivo atual
            current_backup = self.database_path.with_suffix('.db.backup')
            if self.database_path.exists():
                shutil.copy2(self.database_path, current_backup)
            
            # Restaurar
            shutil.copy2(extracted_file, self.database_path)
            
            # Limpar arquivos temporários
            if backup_path.suffix.lower() == '.zip':
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"Backup restaurado com sucesso: {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Lista todos os backups disponíveis"""
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("backup_*.{db,zip}"):
                stat = backup_file.stat()
                
                backup_info = {
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'compressed': backup_file.suffix.lower() == '.zip'
                }
                
                # Tentar extrair metadados se for ZIP
                if backup_file.suffix.lower() == '.zip':
                    try:
                        with zipfile.ZipFile(backup_file, 'r') as zipf:
                            if 'metadata.json' in zipf.namelist():
                                import json
                                metadata = json.loads(zipf.read('metadata.json'))
                                backup_info.update(metadata)
                    except:
                        pass
                
                backups.append(backup_info)
            
            # Ordenar por data de criação (mais recente primeiro)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao listar backups: {e}")
        
        return backups
    
    def cleanup_old_backups(self, keep_days: int = None) -> int:
        """Remove backups antigos"""
        if keep_days is None:
            keep_days = active_config.BACKUP_RETENTION_DAYS
        
        cutoff_time = time.time() - (keep_days * 24 * 3600)
        removed_count = 0
        
        try:
            for backup_file in self.backup_dir.glob("backup_*.{db,zip}"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    removed_count += 1
                    logger.info(f"Backup antigo removido: {backup_file.name}")
            
            if removed_count > 0:
                logger.info(f"Limpeza concluída: {removed_count} backups removidos")
            
        except Exception as e:
            logger.error(f"Erro na limpeza de backups: {e}")
        
        return removed_count
    
    def start_automatic_backup(self, interval_hours: int = None) -> bool:
        """Inicia backup automático"""
        if self.running:
            logger.warning("Backup automático já está rodando")
            return False
        
        if interval_hours is None:
            interval_hours = active_config.BACKUP_INTERVAL // 3600
        
        try:
            # Agendar backup
            schedule.every(interval_hours).hours.do(self._scheduled_backup)
            
            # Agendar limpeza diária
            schedule.every().day.at("02:00").do(self.cleanup_old_backups)
            
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            
            logger.info(f"Backup automático iniciado (intervalo: {interval_hours}h)")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar backup automático: {e}")
            return False
    
    def stop_automatic_backup(self) -> bool:
        """Para backup automático"""
        if not self.running:
            return True
        
        try:
            self.running = False
            schedule.clear()
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
            
            logger.info("Backup automático parado")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar backup automático: {e}")
            return False
    
    def _scheduled_backup(self):
        """Executa backup agendado"""
        try:
            backup_path = self.create_backup(compress=True)
            if backup_path:
                logger.info(f"Backup automático criado: {backup_path}")
                
                # Executar limpeza se necessário
                if self.stats['backups_created'] % 10 == 0:  # A cada 10 backups
                    self.cleanup_old_backups()
            else:
                logger.error("Falha no backup automático")
                
        except Exception as e:
            logger.error(f"Erro no backup agendado: {e}")
    
    def _run_scheduler(self):
        """Thread do agendador"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Verificar a cada minuto
            except Exception as e:
                logger.error(f"Erro no agendador de backup: {e}")
                time.sleep(60)
    
    def _verify_backup_integrity(self, backup_file: Path) -> bool:
        """Verifica integridade do backup"""
        try:
            with sqlite3.connect(str(backup_file)) as conn:
                # Verificar integridade
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result[0] != 'ok':
                    return False
                
                # Verificar se tabelas principais existem
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                
                required_tables = {'usuarios', 'produtos', 'responsaveis'}
                existing_tables = {table[0] for table in tables}
                
                return required_tables.issubset(existing_tables)
                
        except Exception as e:
            logger.error(f"Erro ao verificar integridade do backup: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do serviço de backup"""
        return {
            **self.stats,
            'backup_directory': str(self.backup_dir),
            'automatic_backup_running': self.running,
            'available_backups': len(list(self.backup_dir.glob("backup_*.{db,zip}"))),
            'disk_space_mb': round(
                sum(f.stat().st_size for f in self.backup_dir.glob("*")) / (1024 * 1024), 2
            )
        }

# Instância global
backup_service = BackupService()


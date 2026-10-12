import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

class Store:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.assets = self.root / 'assets'
        self.assets.mkdir(exist_ok=True)
        self.db = self.root / 'forge3d.sqlite3'
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, record TEXT NOT NULL)')

    def connect(self):
        connection = sqlite3.connect(self.db, timeout=15)
        return connection

    def create(self, name, provider, options, kind='generate', parent=None, initial_status='queued'):
        record = {'id':uuid.uuid4().hex,'name':name[:80], 'provider':provider,'options':options,'kind':kind,'parent':parent,'status':initial_status,'stage':'Na fila','created_at':now(),'updated_at':now(),'error':None,'artifacts':{},'metadata':{}}
        self.directory(record['id']).mkdir()
        with self.connect() as connection:
            connection.execute('INSERT INTO jobs VALUES (?,?)',(record['id'],json.dumps(record)))
        return record

    def directory(self, identifier):
        if len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):
            raise ValueError('Identificador inválido')
        return self.assets / identifier

    def get(self, identifier):
        with self.connect() as connection:
            row = connection.execute('SELECT record FROM jobs WHERE id=?',(identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit=200):
        with self.connect() as connection:
            rows = connection.execute('SELECT record FROM jobs ORDER BY rowid DESC'+(' LIMIT ?' if limit is not None else ''), (limit,) if limit is not None else ()).fetchall()
        return [json.loads(row[0]) for row in rows]

    def update(self, identifier, **changes):
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row = connection.execute('SELECT record FROM jobs WHERE id=?',(identifier,)).fetchone()
            if not row:
                raise ValueError('Asset não encontrado')
            record = json.loads(row[0])
            if record['status']=='cancelled':
                return record
            record.update(changes,updated_at=now())
            connection.execute('UPDATE jobs SET record=? WHERE id=?',(json.dumps(record),identifier))
        return record

    def claim_next(self):
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=connection.execute("SELECT id,record FROM jobs WHERE json_extract(record,'$.status')='queued' ORDER BY rowid ASC LIMIT 1").fetchone()
            if not row:
                return None
            record=json.loads(row[1])
            record.update(status='running',stage='Preparando processo local',updated_at=now())
            connection.execute('UPDATE jobs SET record=? WHERE id=?',(json.dumps(record),row[0]))
            return record

    def complete_candidate_batch(self, identifier, children, choices, metadata, artifacts):
        """Publish parent and all staged children in one cancellation-aware commit."""
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=connection.execute('SELECT record FROM jobs WHERE id=?',(identifier,)).fetchone()
            if not row:raise RuntimeError('Lote ausente.')
            parent=json.loads(row[0])
            if parent['status'] in ['cancelled','failed','completed']:raise RuntimeError('Lote encerrado; candidatos não publicados.')
            expected=(parent['options'].get('candidate_count') or 3) if parent['options'].get('quality_mode') else 2
            if len(children)!=expected or len(set(children))!=expected:raise RuntimeError('Quantidade de candidatos distintos não corresponde ao lote.')
            if [choice['id'] for choice in choices]!=children:raise RuntimeError('Seleção inconsistente com candidatos publicados.')
            for child_id in children:
                row=connection.execute('SELECT record FROM jobs WHERE id=?',(child_id,)).fetchone()
                if not row:raise RuntimeError('Candidato ausente.')
                child=json.loads(row[0])
                if child['parent']!=identifier or child['status']!='uploading':raise RuntimeError('Candidato não está pronto para publicação.')
                child['metadata']['character_candidates']=choices
                child.update(status='completed',stage='Candidato preservado',error=None,updated_at=now())
                connection.execute('UPDATE jobs SET record=? WHERE id=?',(json.dumps(child),child_id))
            parent.update(status='completed',stage='Pronto',error=None,metadata={**metadata,'character_candidates':choices},artifacts=artifacts,updated_at=now())
            connection.execute('UPDATE jobs SET record=? WHERE id=?',(json.dumps(parent),identifier))
        return parent

    def cancel(self, identifier):
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            row=connection.execute('SELECT record FROM jobs WHERE id=?',(identifier,)).fetchone()
            if not row:
                raise ValueError('Asset não encontrado.')
            record=json.loads(row[0])
            if record['status'] in ['completed','failed','cancelled']:
                raise ValueError('Este processamento já terminou.')
            record.update(status='cancelled',stage='Cancelado',updated_at=now())
            connection.execute('UPDATE jobs SET record=? WHERE id=?',(json.dumps(record),identifier))
            return record

    def recover(self):
        for job in self.list(limit=None):
            if job['status'] not in ['queued','completed','failed','cancelled']:
                self.update(job['id'],status='failed',stage='Interrompido',error='Processamento interrompido ao fechar o aplicativo. Gere novamente; original preservado.')

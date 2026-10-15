import asyncio
import hashlib
import io
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
from .contracts import ModelWorkflowOptions, TextureWorkflowOptions
from .planner import capabilities, model_plan, texture_plan
from .catalog import catalog
from ..config import atomic_json


def digest(value):
    return hashlib.sha256(value).hexdigest()


async def read_reference(upload):
    body = await upload.read(20 * 1024 * 1024 + 1)
    if len(body) > 20 * 1024 * 1024:
        raise HTTPException(413, 'Cada referência deve ter até 20 MB.')
    try:
        image = Image.open(io.BytesIO(body))
        if image.format not in ['PNG', 'JPEG', 'WEBP'] or min(image.size) < 16 or image.width * image.height > 25_000_000:
            raise ValueError('Use PNG, JPG ou WEBP entre 16 px e 25 megapixels.')
        image.load()
        return body, ImageOps.exif_transpose(image).convert('RGBA')
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(400, 'Imagem inválida. ' + str(error))


def existing_request(store, key, fingerprint):
    if not key:
        return None
    for job in store.list(limit=None):
        manifest = job['metadata'].get('workflow', {})
        if manifest.get('request_key') == key:
            if manifest.get('fingerprint') != fingerprint:
                raise HTTPException(409, 'Esta solicitação já foi usada com outra entrada. Inicie uma nova geração.')
            return job
    return None


def manifest(domain, settings, fingerprint, warnings):
    return {'schema': 1, 'domain': domain, 'settings': settings.model_dump(), 'request_key': settings.request_key,
            'fingerprint': fingerprint, 'warnings': warnings, 'steps': [], 'result': 'pending'}


def saved_references(store, parent):
    result = {}
    seen = set()
    current = parent
    # Prefer the closest texture version, then the generation reference.
    while current:
        if current['id'] in seen:
            raise HTTPException(409, 'O histórico do modelo contém um ciclo.')
        seen.add(current['id'])
        folder = store.directory(current['id'])
        for view in ['front', 'back', 'left', 'right']:
            path = folder / 'references' / view / 'source.png'
            if view not in result and path.is_file() and path.resolve().is_relative_to(store.assets):
                result[view] = path
        if 'front' not in result:
            path = folder / 'prepared_masked.png'
            if path.is_file():
                result['front'] = path
        current = store.get(current['parent']) if current.get('parent') else None
    return result


def workflow_router(root, store, enqueue_generation):
    router = APIRouter()
    lock = asyncio.Lock()

    @router.get('/api/workflows/capabilities')
    def available():
        return capabilities(root)

    @router.get('/api/library')
    def library():
        return catalog(store)

    @router.get('/api/workflows/{identifier}/references')
    def references(identifier: str):
        parent = store.get(identifier)
        if not parent:
            raise HTTPException(404, 'Modelo não encontrado.')
        return {name: '/api/files/' + path.relative_to(store.assets).as_posix()
                for name, path in saved_references(store, parent).items()}

    @router.post('/api/workflows/model', status_code=201)
    async def model(image: UploadFile = File(...), options: str = Form('{}')):
        try:
            settings = ModelWorkflowOptions.model_validate_json(options)
        except ValueError as error:
            raise HTTPException(422, str(error))
        payload, _ = await read_reference(image)
        fingerprint = digest(payload + json.dumps(settings.model_dump(exclude={'request_key'}), sort_keys=True).encode())
        async with lock:
            previous = existing_request(store, settings.request_key, fingerprint)
            if previous:
                return previous
            provider, native, warnings = model_plan(root, settings)
            workflow = manifest('model', settings, fingerprint, warnings)
            workflow['provider'] = provider
            await image.seek(0)
            return await enqueue_generation(image, json.dumps(native), provider, workflow=workflow)

    @router.post('/api/workflows/{identifier}/texture', status_code=201)
    async def texture(identifier: str, options: str = Form('{}'), front: UploadFile | None = File(None),
                      left: UploadFile | None = File(None), back: UploadFile | None = File(None), right: UploadFile | None = File(None)):
        parent = store.get(identifier)
        if not parent:
            raise HTTPException(404, 'Modelo não encontrado.')
        source = store.directory(identifier) / 'model.glb'
        if parent['status'] != 'completed' or not source.is_file():
            raise HTTPException(409, 'Escolha um modelo que já esteja pronto.')
        try:
            settings = TextureWorkflowOptions.model_validate_json(options)
        except ValueError as error:
            raise HTTPException(422, str(error))
        references = {}
        for view, upload in [('front', front), ('left', left), ('back', back), ('right', right)]:
            if upload:
                references[view] = await read_reference(upload)
        if settings.use_saved_references:
            for view, path in saved_references(store, parent).items():
                if view not in references:
                    references[view] = (path.read_bytes(), Image.open(path).convert('RGBA'))
        if 'front' not in references:
            raise HTTPException(422, 'Adicione uma imagem frontal para orientar a aparência do modelo.')
        if settings.background_mode == 'preserve_alpha' and any(image.getchannel('A').getextrema()[0] == 255 for _, image in references.values()):
            raise HTTPException(422, 'Esta imagem não tem transparência. Selecione Remover fundo nas opções avançadas.')
        source_hash = digest(source.read_bytes())
        content = json.dumps({'source': source_hash, 'parent': identifier, 'settings': settings.model_dump(exclude={'request_key'}),
                              'references': {view: digest(body) for view, (body, _) in references.items()}}, sort_keys=True).encode()
        fingerprint = digest(content)
        async with lock:
            previous = existing_request(store, settings.request_key, fingerprint)
            if previous:
                return previous
            native, warnings = texture_plan(root, settings, parent)
            workflow = manifest('texture', settings, fingerprint, warnings)
            workflow.update(provider=native['provider'], source_sha256=source_hash)
            job = store.create(parent['name'] + ' · Textura', parent['provider'], native, kind='texture_workflow', parent=identifier, initial_status='uploading')
            directory = store.directory(job['id'])
            bundle = {}
            for view, (body, image) in references.items():
                target = directory / 'references' / view
                target.mkdir(parents=True)
                (target / 'source_upload.bin').write_bytes(body)
                image.save(target / 'source.png')
                bundle[view] = {'path': f'references/{view}/source.png', 'sha256': digest((target / 'source.png').read_bytes())}
            atomic_json(directory / 'texture_references.json', {'views': bundle})
            atomic_json(directory / 'workflow.json', workflow)
            return store.update(job['id'], status='queued', metadata={'workflow': workflow})

    @router.post('/api/workflows/{identifier}/retry', status_code=201)
    async def retry(identifier: str):
        async with lock:
            original = store.get(identifier)
            if not original or original['kind'] not in ['model_workflow', 'texture_workflow']:
                raise HTTPException(404, 'Fluxo não encontrado.')
            if original['status'] not in ['failed', 'cancelled']:
                raise HTTPException(409, 'A tentativa só pode ser refeita depois de terminar ou ser cancelada.')
            # Repeated retry clicks return the same active attempt.
            for item in store.list(limit=None):
                if item['metadata'].get('workflow', {}).get('retry_of') == identifier and item['status'] not in ['failed', 'cancelled']:
                    return item
            workflow = dict(original['metadata']['workflow'])
            workflow.update(retry_of=identifier, request_key=None, steps=[], result='pending')
            job = store.create(original['name'], original['provider'], original['options'], kind=original['kind'], parent=original['parent'], initial_status='uploading')
            before, after = store.directory(identifier), store.directory(job['id'])
            for name in ['source.png', 'source_upload.bin', 'references.json', 'texture_references.json', 'character_interpretation.json', 'character_interpretation_original.json']:
                if (before / name).is_file():
                    shutil.copy2(before / name, after / name)
            if (before / 'references').is_dir():
                shutil.copytree(before / 'references', after / 'references')
            # Generation references.json contains absolute paths. Rebind copied inputs.
            if (after / 'references.json').is_file():
                text = (after / 'references.json').read_text(encoding='utf-8').replace(str(before).replace('\\', '\\\\'), str(after).replace('\\', '\\\\'))
                (after / 'references.json').write_text(text, encoding='utf-8')
            atomic_json(after / 'workflow.json', workflow)
            return store.update(job['id'], status='queued', metadata={'workflow': workflow})

    return router

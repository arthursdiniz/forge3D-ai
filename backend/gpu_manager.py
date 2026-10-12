"""Resource policy in the API; CUDA contexts stay in isolated providers."""
import subprocess


def probe_gpu():
    try:
        result=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,memory.used,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        values=result.stdout.strip().splitlines()[0].split(',')
        return {'name':values[0].strip(),'total_mb':int(values[1]),'used_mb':int(values[2]),'driver':values[3].strip()}
    except (OSError,ValueError,IndexError,subprocess.TimeoutExpired):
        return {'name':'GPU indisponível','total_mb':0,'used_mb':0}


def validate_vram(gpu,required_free_mb):
    free=max(0,gpu['total_mb']-gpu['used_mb'])
    if gpu['total_mb']==0:raise RuntimeError('CUDA indisponível: verifique NVIDIA/CUDA antes de gerar.')
    if free<required_free_mb:
        raise RuntimeError(f'VRAM insuficiente: {free} MiB livres, perfil exige aproximadamente {required_free_mb} MiB. Feche outros aplicativos GPU ou escolha um perfil mais leve.')
    return {**gpu,'free_mb':free,'required_free_mb':required_free_mb,'scope':'preflight estimate; allocation can still fail'}


def classify_failure(message):
    lower=str(message).lower()
    if 'out of memory' in lower or 'outofmemoryerror' in lower:
        return {'code':'CUDA_OOM','message':'A GPU ficou sem VRAM. Arquivos anteriores preservados; tente um perfil mais leve ou feche outros aplicativos GPU.','retryable':True}
    if 'cuda unavailable' in lower or 'cuda indisponível' in lower:
        return {'code':'CUDA_UNAVAILABLE','message':'CUDA indisponível neste ambiente de inferência. Confira o diagnóstico local.','retryable':True}
    if 'vram insuficiente' in lower:
        return {'code':'VRAM_PREFLIGHT','message':str(message),'retryable':True}
    if 'blender ausente' in lower:return {'code':'BLENDER_MISSING','message':'Configure o executável Blender nas configurações locais.','retryable':True}
    if 'cancel' in lower:return {'code':'CANCELLED','message':'Processamento cancelado.','retryable':True}
    return {'code':'PROCESSING_FAILED','message':'O processamento falhou. Os detalhes estão no log local; resultados anteriores foram preservados.','retryable':True}

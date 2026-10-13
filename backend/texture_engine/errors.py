from ..gpu_manager import classify_failure

def classify_texture_failure(error):
    text=str(error);lower=text.lower();base=classify_failure(error)
    if base['code']!='PROCESSING_FAILED':return base
    cases=[(['rebake'],'UV_REBAKE_REQUIRED',False),(['geometry identity','world geometry mismatch'],'GEOMETRY_IDENTITY_FAILED',False),(['invalid uv','overlap'],'UV_INVALID',False),(['sha256','weight size mismatch'],'LOCAL_RESOURCES_INVALID',True),(['alpha mask','foreground','unsafe reference'],'REFERENCE_INVALID',False),(['static meshes','empty mesh','external fbx','unsupported static','invalid glb','invalid fbx','error: failed to load'],'IMPORT_INVALID',False),(['não validado'],'PROVIDER_UNAVAILABLE',True)]
    for words,code,retry in cases:
        if any(word in lower for word in words):return {'code':code,'message':text[-2000:],'retryable':retry}
    return base

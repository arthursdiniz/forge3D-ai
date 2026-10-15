"""Optional pinned anime detector. No implicit downloads, GPU or identity score."""
import hashlib
import json
import sys
from pathlib import Path

def detector_available(root):
    root=Path(root)
    try:
        manifest=json.loads((root/'models/texture-face/manifest.json').read_text())
        return all((root/'models/texture-face'/record['path']).is_file() and (root/'models/texture-face'/record['path']).stat().st_size==record['bytes'] for record in manifest['weights']) and (root/'vendor/anime-face-detector/anime_face_detector/detector.py').is_file()
    except (OSError,ValueError,KeyError):return False

def detect_anime(image,root):
    import time
    started=time.perf_counter();root=Path(root)
    if not detector_available(root):return {'status':'unavailable_manual_selection','faces':[],'warnings':['Optional anime detector not installed; choose the region manually.']}
    try:
        import numpy as np
        import torch
        folder=root/'models/texture-face';manifest=json.loads((folder/'manifest.json').read_text())
        for record in manifest['weights']:
            path=(folder/record['path']).resolve()
            if not path.is_relative_to(folder.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Face weight SHA mismatch.')
        vendor=root/'vendor/anime-face-detector'
        for relative,expected in manifest['source_sha256'].items():
            path=(vendor/relative).resolve()
            if not path.is_relative_to(vendor.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Face detector source SHA mismatch.')
        sys.path.insert(0,str(vendor));from anime_face_detector.detector import LandmarkDetector
        torch.set_num_threads(4);detector=LandmarkDetector(folder/'hrnetv2.safetensors','yolov3',folder/'yolov3.safetensors',device='cpu',flip_test=False)
        rgb=np.asarray(image.convert('RGB'));height,width=rgb.shape[:2];predictions=detector(rgb[...,::-1].copy());faces=[]
        for prediction in predictions:
            bbox=prediction['bbox'];points=prediction['keypoints']
            if float(bbox[4])<.8:continue
            box=(bbox[:4]/np.array([width,height,width,height])).clip(0,1).tolist()
            if box[0]>=box[2] or box[1]>=box[3]:continue
            landmarks=[{'index':index,'x':float(point[0]/width),'y':float(point[1]/height),'raw_score':float(point[2]),'reviewed':False} for index,point in enumerate(points)]
            reliable=sum(point['raw_score']>=.65 for point in landmarks)
            faces.append({'box':box,'raw_detection_score':float(bbox[4]),'landmarks':landmarks,'status':'needs_alignment_review','reliable_landmarks':reliable})
        del detector
        return {'status':'reviewable' if faces else 'not_detected_manual_selection','faces':faces,'seconds':round(time.perf_counter()-started,3),'device':'CPU','offline':True,'score_scope':'Uncalibrated detector/landmark responses, not identity/fidelity; raw landmarks may exceed1.','warnings':[] if faces else ['No confident anime face detected; manual selection remains available.']}
    except Exception as error:return {'status':'failed_manual_selection','faces':[],'warnings':[str(error)[-600:]],'device':'CPU','seconds':round(time.perf_counter()-started,3)}

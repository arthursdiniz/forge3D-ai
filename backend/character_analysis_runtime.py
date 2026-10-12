"""Offline CPU-only pose detector in its own dependency environment."""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(ROOT/'cache/character-matplotlib')
os.environ['HF_HUB_OFFLINE']='1'

def no_network(*args,**kwargs):raise RuntimeError('Network disabled during local character analysis.')
socket.socket.connect=no_network;socket.create_connection=no_network

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True);parser.add_argument('--output',required=True);parser.add_argument('--category',default='humanoid');args=parser.parse_args()
    from PIL import Image,ImageDraw,ImageOps
    import numpy as np
    import mediapipe as mp
    from backend.character_understanding import LANDMARK_NAMES,CONNECTIONS,summarize_character
    from backend.config import atomic_json
    started=time.perf_counter();output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    source=ImageOps.exif_transpose(Image.open(args.image)).convert('RGBA')
    rgb=Image.new('RGBA',source.size,'white');rgb.alpha_composite(source);rgb=rgb.convert('RGB')
    model=ROOT/'models/character/pose_landmarker_lite.task'
    if not model.is_file():raise RuntimeError('Pose model missing; run the local character setup script.')
    options=mp.tasks.vision.PoseLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(model),delegate=mp.tasks.BaseOptions.Delegate.CPU),running_mode=mp.tasks.vision.RunningMode.IMAGE,num_poses=1,min_pose_detection_confidence=.5,min_pose_presence_confidence=.5,output_segmentation_masks=False)
    with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
        result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=np.ascontiguousarray(rgb)))
    points={}
    if result.pose_landmarks:
        for name,point in zip(LANDMARK_NAMES,result.pose_landmarks[0]):
            if 0<=point.x<=1 and 0<=point.y<=1:
                points[name]={'x':float(point.x),'y':float(point.y),'z':float(point.z),'visibility':float(point.visibility),'presence':float(point.presence),'source':'mediapipe'}
    report=summarize_character(points,list(source.size),args.category)
    report.update(method='MediaPipe PoseLandmarkerLite CPU',source_sha256=hashlib.sha256(Path(args.image).read_bytes()).hexdigest(),model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),image_size=list(source.size),detected_poses=len(result.pose_landmarks),seconds=round(time.perf_counter()-started,3),offline_network_blocked=True,semantic_conditioning=False,library_version=mp.__version__)
    overlay=rgb.copy();draw=ImageDraw.Draw(overlay)
    for a,b in CONNECTIONS:
        if a in points and b in points:draw.line([(points[a]['x']*rgb.width,points[a]['y']*rgb.height),(points[b]['x']*rgb.width,points[b]['y']*rgb.height)],fill='#ff853c',width=max(1,rgb.width//300))
    for name,point in points.items():
        x=point['x']*rgb.width;y=point['y']*rgb.height;r=max(2,rgb.width//200)
        draw.ellipse((x-r,y-r,x+r,y+r),fill='#55c764' if name in report['reliable_landmarks'] else '#ffc54f')
    overlay.save(output/'pose_overlay.png');atomic_json(output/'analysis.json',report)
    print(json.dumps({'passed':True,'detected_poses':len(result.pose_landmarks),'reliable_landmarks':len(report['reliable_landmarks']),'seconds':report['seconds']}),flush=True)

if __name__=='__main__':main()

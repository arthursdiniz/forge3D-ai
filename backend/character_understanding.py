"""Editable pose interpretation; no invented anatomy or generative conditioning."""
import math

LANDMARK_NAMES=['nose','left_eye_inner','left_eye','left_eye_outer','right_eye_inner','right_eye','right_eye_outer','left_ear','right_ear','left_mouth','right_mouth','left_shoulder','right_shoulder','left_elbow','right_elbow','left_wrist','right_wrist','left_pinky','right_pinky','left_index','right_index','left_thumb','right_thumb','left_hip','right_hip','left_knee','right_knee','left_ankle','right_ankle','left_heel','right_heel','left_foot_index','right_foot_index']
MANUAL_NAMES=['head_top','chin','neck','pelvis','head_center']
REGION_NAMES=['head','face','neck','torso','hips','left_arm','right_arm','left_hand','right_hand','left_leg','right_leg','left_foot','right_foot','hair','clothing','accessories']
CONNECTIONS=[('left_shoulder','right_shoulder'),('left_shoulder','left_elbow'),('left_elbow','left_wrist'),('right_shoulder','right_elbow'),('right_elbow','right_wrist'),('left_shoulder','left_hip'),('right_shoulder','right_hip'),('left_hip','right_hip'),('left_hip','left_knee'),('left_knee','left_ankle'),('right_hip','right_knee'),('right_knee','right_ankle')]


def validate_landmarks(points):
    if not isinstance(points,dict) or len(points)>len(LANDMARK_NAMES)+len(MANUAL_NAMES):raise ValueError('Landmarks inválidos.')
    result={}
    for name,point in points.items():
        if name not in LANDMARK_NAMES+MANUAL_NAMES:raise ValueError('Nome de landmark desconhecido: '+name)
        x=float(point['x']);y=float(point['y'])
        if not math.isfinite(x+y) or not (0<=x<=1 and 0<=y<=1):raise ValueError('Landmark fora da imagem.')
        source=point.get('source','manual')
        if source not in ['manual','mediapipe']:raise ValueError('Origem de landmark inválida.')
        item={'x':x,'y':y,'source':source,'reviewed':bool(point.get('reviewed',source=='manual')),'visibility':None,'presence':None}
        if source=='mediapipe':
            for key in ['visibility','presence']:
                value=point.get(key)
                if value is not None:
                    value=float(value)
                    if not math.isfinite(value) or not 0<=value<=1:raise ValueError('Confiança inválida.')
                    item[key]=value
        if point.get('z') is not None:
            z=float(point['z'])
            if not math.isfinite(z):raise ValueError('Profundidade estimada inválida.')
            item['estimated_z']=z
        result[name]=item
    return result


def trusted(point,threshold=.65):
    if point['source']=='manual':return point.get('reviewed',False)
    return point.get('visibility') is not None and point['visibility']>=threshold and point.get('presence') is not None and point['presence']>=threshold


def summarize_character(points,image_size,category='humanoid',pose='unknown',view='unknown',manual_regions=None):
    points=validate_landmarks(points)
    width,height=image_size
    reliable={name:point for name,point in points.items() if trusted(point)}
    uncertain=[name for name in points if name not in reliable]
    proportions={}
    def distance(a,b):return math.hypot((a['x']-b['x'])*width,(a['y']-b['y'])*height)
    def midpoint(a,b):return {'x':(a['x']+b['x'])/2,'y':(a['y']+b['y'])/2}
    if category not in ['nonhuman','custom'] and all(name in reliable for name in ['left_shoulder','right_shoulder','left_hip','right_hip']):
        shoulder=midpoint(reliable['left_shoulder'],reliable['right_shoulder']);hips=midpoint(reliable['left_hip'],reliable['right_hip'])
        torso=distance(shoulder,hips)
        if torso>max(width,height)*.01:
            pairs={'shoulder_width':('left_shoulder','right_shoulder'),'hip_width':('left_hip','right_hip'),'left_upper_arm':('left_shoulder','left_elbow'),'left_forearm':('left_elbow','left_wrist'),'right_upper_arm':('right_shoulder','right_elbow'),'right_forearm':('right_elbow','right_wrist'),'left_thigh':('left_hip','left_knee'),'left_shin':('left_knee','left_ankle'),'right_thigh':('right_hip','right_knee'),'right_shin':('right_knee','right_ankle'),'head_height':('head_top','chin')}
            for name,(a,b) in pairs.items():
                if a in reliable and b in reliable:
                    proportions[name+'_to_torso']={'value':distance(reliable[a],reliable[b])/torso,'scope':'projected_2d_ratio','source_landmarks':[a,b],'uncertainty':'Perspective/occlusion and pose affect this ratio; no universal human target imposed.'}
    regions={name:{'status':'unknown','bounds':None,'source':'not_segmented','confidence':None} for name in REGION_NAMES}
    groups={'torso':['left_shoulder','right_shoulder','left_hip','right_hip'],'hips':['left_hip','right_hip'],'head':['nose','left_ear','right_ear','head_top','chin'],'face':['nose','left_eye','right_eye','left_mouth','right_mouth'],'neck':['left_shoulder','right_shoulder','chin'],'left_arm':['left_shoulder','left_elbow','left_wrist'],'right_arm':['right_shoulder','right_elbow','right_wrist'],'left_hand':['left_wrist','left_index','left_pinky','left_thumb'],'right_hand':['right_wrist','right_index','right_pinky','right_thumb'],'left_leg':['left_hip','left_knee','left_ankle'],'right_leg':['right_hip','right_knee','right_ankle'],'left_foot':['left_ankle','left_heel','left_foot_index'],'right_foot':['right_ankle','right_heel','right_foot_index']}
    for name,names in groups.items():
        values=[reliable[key] for key in names if key in reliable]
        if len(values)>=2:
            padding=.015
            regions[name]={'status':'estimated_from_landmarks','source':'landmark_bounds_not_semantic_segmentation','confidence':None,'bounds':[max(0,min(p['x'] for p in values)-padding),max(0,min(p['y'] for p in values)-padding),min(1,max(p['x'] for p in values)+padding),min(1,max(p['y'] for p in values)+padding)]}
    for name,box in (manual_regions or {}).items():
        import re
        if (name not in REGION_NAMES and not re.fullmatch(r'custom_[a-zA-Z0-9_]{1,48}',name)) or len(box)!=4:raise ValueError('Região manual inválida; partes personalizadas usam prefixo custom_.')
        l,t,r,b=map(float,box)
        if not (0<=l<r<=1 and 0<=t<b<=1):raise ValueError('Caixa de região manual inválida.')
        regions[name]={'status':'user_defined','source':'manual','confidence':None,'bounds':[l,t,r,b]}
    warnings=['Landmarks são hipóteses de pose; visibility/presence não medem anatomia correta.','Cabelo, roupa e acessórios não são segmentados automaticamente; marque regiões manualmente quando necessário.','A interpretação não condiciona a rede 3D single-image; serve comparação e modelagem assistida.']
    if len(reliable)<8:warnings.append('Poucos landmarks confiáveis; revise os pontos antes de medir proporções ou criar base mesh.')
    if category in ['anime','cartoon','nonhuman','custom']:warnings.append('Detector treinado em pessoas pode falhar neste estilo; não impor proporções humanas realistas.')
    if pose not in ['a_pose','t_pose','neutral']:warnings.append('Pose incerta/dinâmica: simetria automática desativada.')
    return {'status':'reviewable' if len(reliable)>=8 else 'needs_manual_review','category':category,'pose':pose,'view':view,'landmarks':points,'reliable_landmarks':list(reliable),'uncertain_landmarks':uncertain,'regions':regions,'proportions':proportions,'symmetry_automatic_allowed':False,'symmetry_reviewable':pose in ['a_pose','t_pose','neutral'] and view=='front','anatomy_constraints_enforced':False,'confidence_scope':'landmark visibility/presence only; not calibrated anatomical accuracy','warnings':warnings}

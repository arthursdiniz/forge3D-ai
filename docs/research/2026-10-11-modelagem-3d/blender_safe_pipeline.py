"""Research harness: snapshot color layer name before Blender edit-mode rebuild.

The product source is read and never modified. Edit-mode synchronization
invalidated its retained RNA color attribute in the real vertex-bake test.
"""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
source_path=root/'blender/pipeline.py'
source=source_path.read_text(encoding='utf-8')
old='        color=obj.data.color_attributes.active_color\n'
new=old+'        color_layer_name=color.name if color else None\n'
assert source.count(old)==1
assert source.count('vertex.layer_name=color.name')==1
source=source.replace(old,new).replace('vertex.layer_name=color.name','vertex.layer_name=color_layer_name')
sys.path.insert(0,str(root))
exec(compile(source,str(source_path),'exec'),{'__name__':'__main__','__file__':str(source_path)})

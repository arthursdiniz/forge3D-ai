from PIL import Image
from backend.preprocess import prepare_image

def test_provider_background_is_white_without_erasing_alpha(tmp_path):
    source=tmp_path/'image.png';output=tmp_path/'prepared.png'
    image=Image.new('RGBA',(300,300),(0,0,0,0));image.paste((255,0,0,255),(100,60,200,250));image.save(source)
    original=source.read_bytes()
    report=prepare_image(source,output,background_mode='auto',background_color=(255,255,255),foreground_ratio=5/6)
    assert Image.open(output).getpixel((0,0))==(255,255,255)
    assert Image.open(output).getpixel((256,256))==(255,0,0)
    assert report['background_color']==[255,255,255]
    assert report['background_action']=='preserved_alpha'
    assert source.read_bytes()==original

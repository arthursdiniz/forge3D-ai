from PIL import Image

def test_optional_alpha_canvas_preserves_holes_and_leaves_encoder_rgb_identical(tmp_path):
    from backend.preprocess import prepare_image
    source=tmp_path/'source.png'
    image=Image.new('RGBA',(100,100),(200,50,10,255))
    image.paste((0,0,0,0),(40,40,60,60));image.save(source)
    before=tmp_path/'old.png';after=tmp_path/'prepared.png'
    prepare_image(source,before,background_mode='preserve_alpha',background_color=(255,255,255))
    prepare_image(source,after,background_mode='preserve_alpha',background_color=(255,255,255),save_alpha=True)
    assert before.read_bytes()==after.read_bytes()
    mask=Image.open(tmp_path/'prepared_alpha.png')
    assert mask.mode=='RGBA' and mask.size==(512,512)
    assert mask.getpixel((256,256))[3]==0
    assert mask.getpixel((160,160))[3]>250

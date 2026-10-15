"""Shared categorical vocabulary; no numerical imports in the API runtime."""
CLASS_NAMES=['unknown','background','skin','face','hair','eyes','mouth','clothes','eyebrows','nose','ears','neck','arms','legs','hands','feet','upper_clothes','lower_clothes','sleeves','socks','shoes','accessory','held_object','decoration','custom']
NATIVE_MAPPING={0:1,1:4,2:5,3:6,4:3,5:2,6:7}
CLASS_IDS={name:index for index,name in enumerate(CLASS_NAMES)}
SUPPORTED=['background','skin','face','hair','eyes','mouth','clothes']
FACIAL_IDS={3,5,6,8,9,10}

def compatible_labels(a,b):
    return a==b or (a in [2,3] and b in [2,3])

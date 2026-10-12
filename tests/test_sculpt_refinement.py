import numpy as np


def test_selective_micro_refinement_preserves_boundary_and_displacement_bound():
    from backend.sculpt_refinement import refine_surface
    n=9
    vertices=np.array([[x/(n-1),y/(n-1),.02 if x==4 and y==4 else 0] for y in range(n) for x in range(n)],float)
    faces=[]
    for y in range(n-1):
        for x in range(n-1):
            a=y*n+x;faces.extend([[a,a+1,a+n],[a+1,a+n+1,a+n]])
    selected=np.ones(len(vertices),bool)
    result,report=refine_surface(vertices,np.array(faces),selected,strength=.2,iterations=2,max_displacement_ratio=.005)
    assert report['accepted'] and result[40,2]<vertices[40,2]
    assert np.max(np.linalg.norm(result-vertices,axis=1))<=.005+1e-9
    assert np.array_equal(result[:n],vertices[:n])
    assert report['faces_changed']==0


def test_sharp_feature_vertices_are_not_smoothed():
    from backend.sculpt_refinement import refine_surface
    vertices=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
    faces=np.array([[0,1,2],[0,3,1],[0,2,3],[1,3,2]])
    result,report=refine_surface(vertices,faces,np.ones(4,bool),strength=.2)
    assert np.array_equal(result,vertices)
    assert report['accepted'] is False

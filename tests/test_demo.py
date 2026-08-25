import numpy as np
from histometpath_web.demo import EXAMPLES,aggregate,make_slide,sample_indices

def test_examples_are_deterministic():
    for name in EXAMPLES:
        a,b=make_slide(name),make_slide(name)
        assert a.equals(b) and len(a)==144

def test_aggregations_are_bounded():
    x=np.array([.1,.4,.8])
    for method in ["Mean pooling","Max pooling","Attention pooling"]:
        score,w=aggregate(x,method);assert 0<=score<=1;assert np.isclose(w.sum(),1)

def test_sampling_unique_and_sized():
    df=make_slide("Spatially heterogeneous")
    for method in ["Random","Quality weighted","Spatial coverage"]:
        idx=sample_indices(df,method,24);assert len(idx)==24;assert len(set(idx))==24

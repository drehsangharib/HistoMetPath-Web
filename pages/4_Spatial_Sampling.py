import streamlit as st
import plotly.express as px
from histometpath_web.demo import EXAMPLES,make_slide,sample_indices
from histometpath_web.ui import configure,footer
configure("Spatial Sampling")
st.title("Spatial sampling explorer")
name=st.selectbox("Example",list(EXAMPLES));n=st.slider("Tiles to sample",8,64,28,4);df=make_slide(name)
methods=["Random","Quality weighted","Spatial coverage"]
cols=st.columns(3)
for col,method in zip(cols,methods):
 idx=sample_indices(df,method,n);view=df.copy();view["selected"]=False;view.loc[idx,"selected"]=True
 fig=px.scatter(view,x="x",y="y",color="selected",symbol="selected",title=method,color_discrete_map={True:"#e45756",False:"#d7dde3"});fig.update_yaxes(autorange="reversed",scaleanchor="x");col.plotly_chart(fig,width='stretch');col.metric("Mean tissue quality",f"{df.loc[idx,'tissue_quality'].mean():.2f}")
st.info("The spatial-coverage example is a deterministic educational approximation, not the frozen research sampler implementation.")
footer()

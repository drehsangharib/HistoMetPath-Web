import streamlit as st
import plotly.express as px
from histometpath_web.demo import EXAMPLES,make_slide,aggregate
from histometpath_web.ui import configure,footer
configure("MIL Explorer")
st.title("MIL aggregation explorer")
name=st.selectbox("Example",list(EXAMPLES));method=st.radio("Aggregation",["Mean pooling","Max pooling","Attention pooling"],horizontal=True);df=make_slide(name);score,weights=aggregate(df.embedding_score.to_numpy(),method);df["weight"]=weights
c1,c2=st.columns([1,1]);c1.metric("Demonstration slide score",f"{score:.3f}");c1.write("Change aggregation methods to see how diffuse versus focal evidence affects the slide score.")
fig=px.scatter(df,x="x",y="y",color="weight",size="weight",color_continuous_scale="Viridis",title="Tile contribution weights");fig.update_yaxes(autorange="reversed",scaleanchor="x");c2.plotly_chart(fig,width='stretch')
st.dataframe(df.nlargest(10,"weight")[["x","y","embedding_score","weight","tile_label"]],width='stretch',hide_index=True)
st.warning("Attention weights describe model allocation in this educational example; they are not causal explanations or clinical evidence.")
footer()

import streamlit as st
import plotly.express as px
from histometpath_web.demo import EXAMPLES,make_slide
from histometpath_web.ui import configure,footer
configure("Pseudo-Slide Explorer")
st.title("Pseudo-slide explorer")
name=st.selectbox("Bundled educational example",list(EXAMPLES))
df=make_slide(name)
c1,c2,c3=st.columns(3);c1.metric("Tiles",len(df));c2.metric("Positive tiles",int(df.tile_label.sum()));c3.metric("Positive fraction",f"{df.tile_label.mean():.1%}")
fig=px.scatter(df,x="x",y="y",color="embedding_score",size="tissue_quality",color_continuous_scale="Tealrose",title="Synthetic tile landscape",hover_data=["tile_label","signal"]);fig.update_yaxes(autorange="reversed",scaleanchor="x");st.plotly_chart(fig,width='stretch')
st.caption("Generated demonstration data. No patient data, WSI pixels, or external cohort artifacts are used.")
footer()

"""Lenguaje visual de gráficos del Observatorio Humanitario OPS.

Rediseño independiente del dashboard El Niño: eje comparativo en horizontal,
puntos etiquetados, series temporales limpias, color por significado (no por
decoración), notas de cobertura por separado y sin leyendas innecesarias.
"""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go

NAVY="#004B87"
BLUE="#0072CE"
TEAL="#008C95"
ORANGE="#E87C2A"
LIGHT="#A7CFE4"
INK="#17324D"
MUTED="#657988"
GRID="#E7EEF3"
PAPER="#FFFFFF"
SERIES=[BLUE,TEAL,ORANGE,"#6758A4","#4C85AC","#AA705F"]

def finish(fig:go.Figure,*,height=400,orient="default",units="",zero=True):
    """Preparar figura legible en desktop/mobile sin etiquetas superpuestas."""
    fig.update_layout(
        template="none",height=height,
        paper_bgcolor=PAPER,plot_bgcolor=PAPER,
        font=dict(family="Arial,sans-serif",size=12,color=INK),
        margin=dict(l=12,r=42,t=20,b=48),
        hoverlabel=dict(bgcolor="white",bordercolor=GRID,font_size=12),
        showlegend=False,
        transition_duration=150,
        uniformtext=dict(minsize=9,mode="hide"),
    )
    fig.update_xaxes(showline=False,showgrid=False,zeroline=False,
        ticks="",tickfont=dict(color=MUTED,size=11),title_font_size=11)
    fig.update_yaxes(showline=False,showgrid=False,zeroline=False,
        ticks="",tickfont=dict(color=INK,size=11),title_font_size=11)
    if orient=="horizontal":
        fig.update_xaxes(showgrid=True,gridcolor=GRID,gridwidth=1,
            rangemode="tozero" if zero else "normal",title_text=units or None)
        fig.update_yaxes(showgrid=False,title_text=None,automargin=True)
    elif orient=="temporal":
        fig.update_yaxes(showgrid=True,gridcolor=GRID,title_text=units or None)
        fig.update_xaxes(showgrid=False,title_text=None)
    elif orient=="vertical":
        fig.update_yaxes(showgrid=True,gridcolor=GRID,
            rangemode="tozero" if zero else "normal",title_text=units or None)
        fig.update_xaxes(showgrid=False,title_text=None)
    return fig

def rank_bars(df:pd.DataFrame,*,label:str,value:str,limit=13,
              color=BLUE,units="",max_x=None,formats=".1f",
              hover_extra=None):
    """Ranking horizontal pequeño: etiqueta legible, valores a la derecha."""
    frame=df[[label,value]+([hover_extra] if hover_extra and hover_extra in df else [])].copy()
    frame[value]=pd.to_numeric(frame[value],errors="coerce")
    frame=frame.dropna(subset=[value]).nlargest(limit,value).sort_values(value)
    fig=go.Figure()
    labels=frame[label].astype(str).tolist()
    vals=frame[value].tolist()
    fig.add_trace(go.Bar(
        y=labels,x=vals,orientation="h",
        marker=dict(color=[color if i>=len(vals)-3 else LIGHT for i in range(len(vals))],
                    line=dict(width=0)),
        text=[f"{v:,.1f}" if formats==".1f" else f"{v:,.0f}" for v in vals],
        textposition="outside",cliponaxis=False,
        hovertemplate="%{y}<br><b>%{x:,.2f}</b>"+(f" {units}" if units else "")+"<extra></extra>",
    ))
    h=max(280,min(600,62+len(frame)*34))
    finish(fig,height=h,orient="horizontal",units=units)
    if max_x is not None:fig.update_xaxes(range=[0,max_x])
    else:
        vmax=max(vals) if vals else 1
        fig.update_xaxes(range=[0,vmax*1.19 if vmax>0 else 1])
    fig.update_layout(margin=dict(l=12,r=55,t=14,b=43))
    return fig

def trend(df:pd.DataFrame,*,x:str,y:str,units="",color=BLUE,area=True):
    frame=df[[x,y]].copy()
    frame[x]=pd.to_datetime(frame[x],errors="coerce")
    frame[y]=pd.to_numeric(frame[y],errors="coerce")
    frame=frame.dropna().sort_values(x)
    fig=go.Figure()
    if not frame.empty:
        fig.add_trace(go.Scatter(
            x=frame[x],y=frame[y],mode="lines",
            line=dict(color=color,width=2.9,shape="linear"),
            fill="tozeroy" if area else None,
            fillcolor="rgba(0,114,206,0.07)" if area else None,
            hovertemplate="%{x|%b %Y}<br><b>%{y:,.1f}</b>"+
                (f" {units}" if units else "")+"<extra></extra>",
        ))
        fig.add_trace(go.Scatter(x=[frame[x].iloc[-1]],y=[frame[y].iloc[-1]],
            mode="markers",marker=dict(color=color,size=9,line=dict(
                color="white",width=2)),
            hovertemplate="%{x|%b %Y}: <b>%{y:,.1f}</b><extra></extra>"))
    finish(fig,height=340,orient="temporal",units=units)
    fig.update_layout(margin=dict(l=12,r=25,t=17,b=38))
    return fig

def strip_countries(df:pd.DataFrame,*,name="pais",val="valor",
                    year="periodo",max_items=25,units="",decimals=1):
    """Dot plot muestra año en el hover, no codifica edad de datos con gradiente."""
    frame=df[[name,val,year]].copy()
    frame[val]=pd.to_numeric(frame[val],errors="coerce")
    frame=frame.dropna(subset=[val]).sort_values(val,ascending=False).head(max_items)
    frame=frame.sort_values(val)
    fig=go.Figure(go.Scatter(
        x=frame[val],y=frame[name],mode="markers+text",
        marker=dict(size=10,color=BLUE,line=dict(color="white",width=1)),
        text=[f"{x:,.{decimals}f}" for x in frame[val]],textposition="middle right",
        customdata=frame[[year]].to_numpy(),
        hovertemplate=("<b>%{y}</b><br>Valor: %{x:,."+str(decimals)+
                       "f}<br>Año: %{customdata[0]}<extra></extra>"),
    ))
    h=max(300,min(760,70+len(frame)*26))
    finish(fig,height=h,orient="horizontal",units=units)
    maxv=frame[val].max() if len(frame) else 0
    minv=frame[val].min() if len(frame) else 0
    if pd.notna(minv) and minv>=0:
        fig.update_xaxes(range=[0,maxv*1.18 if maxv>0 else 1])
    fig.update_layout(margin=dict(l=12,r=55,t=10,b=43))
    return fig

def severity_matrix(df:pd.DataFrame,*,items=("impacto_crisis","condiciones_afectados","complejidad"),labels=None):
    """Componentes por crisis: puntos comparables en eje común 0–10."""
    labels=labels or {"impacto_crisis":"Impacto de la crisis",
              "condiciones_afectados":"Condiciones de personas afectadas",
              "complejidad":"Complejidad"}
    fig=go.Figure()
    for i,k in enumerate(items):
        v=pd.to_numeric(df.get(k,pd.Series(dtype=float)),errors="coerce")
        vals=v.dropna()
        if vals.empty:continue
        fig.add_trace(go.Box(x=vals,name=labels.get(k,k),orientation="h",
            marker_color=SERIES[i%len(SERIES)],
            boxpoints="all",jitter=.24,pointpos=0,marker_size=6,
            line_width=1,fillcolor="rgba(245,248,250,0.55)"))
    finish(fig,height=285,orient="horizontal",units="Puntuación / 10")
    fig.update_layout(showlegend=False)
    fig.update_xaxes(range=[0,10])
    return fig

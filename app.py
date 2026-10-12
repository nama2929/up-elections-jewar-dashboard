"""Saarthi Jewar AC-63 — sourced, descriptive electoral intelligence (2017–2024).
Local: python -m streamlit run app.py
All polling-station totals are EVM-only, including NOTA in share denominators.
"""
from pathlib import Path
import json
import re
from datetime import date
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from candidate_lab import render_data_lab

st.set_page_config(page_title="Jewar 63 | Saarthi Electoral Lens", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
PAGES=["Overview","Election History","Booth Intelligence","Candidate Landscape","Cross-Year Lens","Issues & Timeline","Game Data Lab","Diagnostics Lab","Research & QA","Meeting Brief"]
PRIMARY="#123547"; TEAL="#168d8a"; BG="#f8faf9"; AMBER="#d68c37"; GREY="#607283"
COLORS={"BJP":"#d88e3c","SP":"#bb4e62","BSP":"#537db4","RLD":"#41957f","INC":"#67779c","IND":"#8e98a0"}

st.markdown("""<style>
:root { color-scheme:light; }
.stApp {background: #f8faf9; color:#172f40;}
.block-container {max-width:1500px; padding-top:1.45rem; padding-bottom:3rem;}
[data-testid="stSidebar"] {background:#edf2f3; border-right:1px solid #dce5e7;}
[data-testid="stMetric"] {padding:1rem 1.05rem; background:white; border:1px solid #e1e8ea; border-radius:14px; box-shadow:0 2px 12px rgba(28,58,69,.035);}
[data-testid="stMetricLabel"]{color:#4b6471!important;font-weight:620;}
[data-testid="stMetricValue"]{color:#123547!important;}
div[data-testid="stPlotlyChart"]{background:white;border:1px solid #e1e8ea;border-radius:13px;padding:.3rem;}
.stButton>button[kind="secondary"] {background:white; border-color:#d4e0e1; color:#123547; border-radius:10px;}
.stButton>button:hover {border-color:#168d8a;color:#168d8a;}
.stDownloadButton>button {border-radius:10px;}
.hero {background:linear-gradient(110deg,#123547,#20596a); color:white; padding:1.6rem 1.9rem; border-radius:18px; margin:.3rem 0 1.35rem; box-shadow:0 5px 17px #152e3c11;}
.hero small{color:#c6e9e8;font-size:.78rem;letter-spacing:.12em;font-weight:700;}
.hero h1{font-size:2.05rem;margin:.3rem 0 .42rem;color:white;font-weight:770;}
.hero p{font-size:.99rem;color:#e0eaeb;margin:0;max-width:1080px;line-height:1.55;}
.kicker{font-size:.73rem;letter-spacing:.12em;color:#627c87;font-weight:750;text-transform:uppercase;margin:.3rem 0 .6rem;}
.section-head {font-size:1.24rem; font-weight:730; color:#123547; margin:1.4rem 0 .65rem;}
.note{padding:.75rem 1rem;background:#eef4f4;border-left:3px solid #168d8a;border-radius:7px;font-size:.94rem;line-height:1.5; margin:.45rem 0 1rem;}
.warning-note{padding:.75rem 1rem;background:#fff8ee;border-left:3px solid #d68c37;border-radius:7px;font-size:.92rem;line-height:1.5; margin:.45rem 0 1rem;}
.footnote{font-size:.78rem;color:#657a85;margin-top:.2rem;line-height:1.5;}
.brand {font-size:1.15rem;font-weight:850;color:#123547;letter-spacing:.13em;}
.brand-sub {font-size:.73rem;letter-spacing:.12em;color:#5a7981;font-weight:700;margin-bottom:1.5rem;}
.source-card {padding:1rem;border:1px solid #dde6e8;border-radius:12px;background:white;margin:.65rem 0;}
div[data-testid="stDataFrame"]{border-radius:10px;overflow:hidden;}
</style>""",unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load_meta():
    return {int(k):v for k,v in json.loads((DATA/'metadata.json').read_text(encoding='utf-8')).items()}

@st.cache_data(show_spinner=False)
def load_year(year):
    d=pd.read_csv(DATA/f'form20_{year}.csv',encoding='utf-8-sig',keep_default_na=False)
    d['station']=pd.to_numeric(d['station'],errors='coerce').astype(int)
    for c in ['evm_votes','nota','qa_diff']+[c for c in d.columns if re.fullmatch(r'V\d+',c)]:
        d[c]=pd.to_numeric(d[c],errors='coerce').fillna(0).astype(int)
    d['electors']=pd.to_numeric(d['electors'],errors='coerce')
    d['turnout_pct']=np.where(d['electors']>0,d['evm_votes']/d['electors']*100,np.nan)
    return d

@st.cache_data(show_spinner=False)
def load_aux(name):
    return pd.read_csv(DATA/name,encoding='utf-8-sig',keep_default_na=False)

META=load_meta()
YEARS=sorted(META)

def fnum(n):return f"{int(n):,}"
def fpct(x):return "—" if pd.isna(x) else f"{x:.2f}%"
def choose_label(c):return f"{c['name']} · {c['party']}" if c['party'] else c['name']

def hero(title,description,code="JEWAR · UTTAR PRADESH · AC 63"):
    st.markdown(f'<div class="hero"><small>{code}</small><h1>{title}</h1><p>{description}</p></div>',unsafe_allow_html=True)

def headline(s):st.markdown(f'<div class="section-head">{s}</div>',unsafe_allow_html=True)
def note(s,warning=False):st.markdown(f'<div class="{ "warning-note" if warning else "note"}">{s}</div>',unsafe_allow_html=True)
def foot(s):st.markdown(f'<p class="footnote">{s}</p>',unsafe_allow_html=True)

def go_page(name):st.session_state['nav']=name


def candidate_frame(year,idx):
    """One station = one dot/record. Margin uses strongest rival, *not* runner-up globally."""
    df=load_year(year).copy()
    cand=META[year]['candidates']
    selected=cand[idx]
    allcols=[c['col'] for c in cand]
    others=[c for c in allcols if c!=selected['col']]
    df['votes']=df[selected['col']]
    df['strongest_rival_votes']=df[others].max(axis=1)
    df['focus_share']=np.where(df['evm_votes']>0,df['votes']*100/df['evm_votes'],np.nan)
    df['signed_margin_pp']=np.where(df['evm_votes']>0,(df['votes']-df['strongest_rival_votes'])*100/df['evm_votes'],np.nan)
    df['leader_col']=df[allcols].idxmax(axis=1)
    names={c['col']:c['name'] for c in cand}
    df['station_leader']=df['leader_col'].map(names)
    df['is_lead']=df['signed_margin_pp']>0
    values=df['focus_share'].dropna()
    q1,med,q3=[float(values.quantile(i)) for i in (.25,.5,.75)]
    df['share_band']=df['focus_share'].apply(lambda v:'No EVM data' if pd.isna(v) else ('Low' if v<q1 else ('Middle' if v<=q3 else 'High')))
    def margin_band(v):
        if pd.isna(v):return 'No EVM data'
        if v<-20:return 'Large deficit'
        if v<-5:return 'Moderate deficit'
        if v<0:return 'Narrow deficit'
        if v==0:return 'Tie'
        if v<=5:return 'Narrow lead'
        if v<=20:return 'Moderate lead'
        return 'Large lead'
    df['margin_band']=df['signed_margin_pp'].apply(margin_band)
    df['candidate_name']=selected['name'];df['candidate_party']=selected['party']
    return df,(q1,med,q3)


def scatter_plot(df,candidate):
    valid=df.dropna(subset=['focus_share','signed_margin_pp']).copy()
    fig=px.scatter(valid,x='focus_share',y='signed_margin_pp',color='share_band',
        color_discrete_map={'Low':'#d48d8b','Middle':'#8da8b5','High':'#168d8a'},
        hover_data={'station':True,'location':True,'votes':True,'focus_share':':.2f','signed_margin_pp':':.2f','share_band':False},
        labels={'focus_share':'Vote share (%)','signed_margin_pp':'Signed margin (percentage points)','share_band':'Share band'},
        opacity=.78)
    fig.add_hline(y=0,line_color='#6a8090',line_dash='dash',line_width=1)
    fig.update_traces(marker={'size':8,'line':{'width':.3,'color':'#ffffff'}})
    fig.update_layout(height=400,margin=dict(l=20,r=15,t=20,b=26),template='plotly_white',legend=dict(orientation='h',y=-.27),hovermode='closest')
    return fig


def distribution_plot(df):
    x=df['focus_share'].dropna()
    fig=go.Figure(go.Histogram(x=x,xbins=dict(start=0,end=100,size=5),marker_color='#168d8a',marker_line_color='white',marker_line_width=.5,opacity=.9,
    hovertemplate='Vote share: %{x:.0f}% bin<br>Stations: %{y:,}<extra></extra>'))
    fig.update_layout(bargap=.03,height=340,margin=dict(l=18,r=10,t=15,b=25),xaxis_title='Station vote share (%) · continuous 5 pp bins',yaxis_title='Number of stations',template='plotly_white')
    return fig


def matrix_fig(df):
    bands=['Low','Middle','High']
    margins=['Large deficit','Moderate deficit','Narrow deficit','Tie','Narrow lead','Moderate lead','Large lead']
    t=pd.crosstab(df['share_band'],df['margin_band']).reindex(index=bands,columns=margins,fill_value=0)
    fig=go.Figure(go.Heatmap(z=t.values,x=['Large<br>deficit','Moderate<br>deficit','Narrow<br>deficit','Tie','Narrow<br>lead','Moderate<br>lead','Large<br>lead'],y=bands,
        text=t.values,texttemplate='%{text}',textfont={'size':15},colorscale=[[0,'#f1f5f6'],[.35,'#9fc8cf'],[1,'#276b7a']],showscale=False,hovertemplate='Band: %{y}<br>Margin: %{x}<br>Stations: %{z}<extra></extra>'))
    fig.update_layout(height=285,margin=dict(l=10,r=10,t=18,b=48),yaxis={'autorange':'reversed'},template='plotly_white',xaxis_tickfont={'size':10})
    return fig,t


def party_color(name):
    p=name.upper()
    for k,v in COLORS.items():
        if k in p:return v
    return '#7994a1'


def candidate_summary(year):
    d=load_year(year);out=[];total=d['evm_votes'].sum()
    for c in META[year]['candidates']:
        vals=d[c['col']];others=[x['col'] for x in META[year]['candidates'] if x['col']!=c['col']]
        leads=int((vals>d[others].max(axis=1)).sum())
        out.append({'Candidate':c['name'],'Party':c['party'],'EVM votes':int(vals.sum()),'Share %':round(100*vals.sum()/total,2) if total else 0,'Station leads':leads,'Focus':c['is_focus']})
    return pd.DataFrame(out).sort_values('EVM votes',ascending=False).reset_index(drop=True)


def year_note(year):
    m=META[year]
    note(f"<b>{year} · {m['election_type']}</b> — {m['alliance']}")

with st.sidebar:
    st.markdown('<div class="brand">SAARTHI</div><div class="brand-sub">ELECTORAL LENS · JEWAR</div>',unsafe_allow_html=True)
    st.radio('Workspace',PAGES,key='nav',label_visibility='collapsed')
    st.divider()
    st.caption('EVIDENCE BASE')
    st.caption('2017 · Assembly | 343 stations')
    st.caption('2019 · Lok Sabha segment | 388')
    st.caption('2022 · Assembly | 419')
    st.caption('2024 · Lok Sabha segment | 398')
    st.divider()
    st.caption('Sourced EVM polling-station data, not current voter-intention measurement. No 2027 forecast.')

page=st.session_state['nav']

if page=='Overview':
    hero('Jewar Constituency Intelligence','A transparent, booth-level historical research workspace for Jewar Assembly Constituency 63. Built from supplied Form 20 records, with every election labelled by candidate, party and alliance.')
    a,b,c,d=st.columns(4)
    a.metric('2017 Narender Nagar · SP votes','13,216')
    b.metric('2017 SP EVM share','6.25%')
    c.metric('2017 Narender station leads','7 / 343')
    d.metric('Station-year records','1,548')
    headline('Explore the research')
    panels=[('Election History','2017 / 2019 / 2022 / 2024 candidate results'),('Booth Intelligence','Vote share · signed margins · quartiles · 2D matrix'),('Candidate Landscape','Every contestant and polling-station lead counts'),('Cross-Year Lens','Separate Assembly and Lok Sabha comparisons'),('Issues & Timeline','Dated reporting, official sources and open questions'),('Game Data Lab','Turn candidates on/off · add new names · adjust hypothetical shares'),('Research & QA','Audit trail, known discrepancies and CSV exports')]
    for i in range(0,len(panels),3):
        cols=st.columns(3)
        for (label,detail),col in zip(panels[i:i+3],cols):
            with col:
                with st.container(border=True):
                    st.markdown(f'**{label}**')
                    st.caption(detail)
                    st.button('Open →',key='home_'+label,on_click=go_page,args=(label,),use_container_width=True)
    headline('Four elections — four different candidate contexts')
    view=[]
    for year in YEARS:
        m=META[year]; view.append({'Year':year,'Ballot':m['election_type'],'Reference candidate':m['focus'],'Party':m['focus_party'],'Candidate EVM votes':m['focus_votes'],'Stations led':m['focus_station_leads'],'Station records':m['stations']})
    st.dataframe(pd.DataFrame(view),hide_index=True,use_container_width=True,column_config={'Candidate EVM votes':st.column_config.NumberColumn(format='%d'),'Stations led':st.column_config.NumberColumn(format='%d')})
    note('<b>Candidate-identity safeguard:</b> Narender Nagar is the 2017 SP Assembly candidate. The 2019 BSP nominee, 2022 RLD nominee and 2024 SP parliamentary nominee are different candidates. Their votes must not be labelled as Narender Nagar’s personal votes.',True)
    foot('Source: your uploaded Jewar Form 20 materials and research workbook. EVM figures are not final declared totals where postal ballots exist.')

elif page=='Election History':
    hero('Election History','Compare vote totals and vote shares by candidate within each election. Parliamentary Jewar segment results are intentionally distinguished from Assembly elections.')
    year=st.select_slider('Choose an election',options=YEARS,value=2017,key='history_year')
    year_note(year)
    d=load_year(year);cands=candidate_summary(year);total=d['evm_votes'].sum()
    top=cands.iloc[0];second=cands.iloc[1]
    a,b,c,dcols=st.columns(4)
    a.metric('Station EVM votes',fnum(total)); b.metric('Leading candidate',top['Candidate']);c.metric('EVM lead over second',fnum(top['EVM votes']-second['EVM votes']));dcols.metric('Stations',len(d))
    col1,col2=st.columns([1.35,1])
    with col1:
        headline('All candidates · EVM votes')
        chart=cands.head(10).sort_values('EVM votes',ascending=True)
        fig=go.Figure(go.Bar(x=chart['EVM votes'],y=chart['Candidate'],orientation='h',marker_color=[COLORS.get(p,'#90a6b0') for p in chart['Party']],text=chart['EVM votes'],textposition='outside',cliponaxis=False))
        fig.update_layout(height=max(320,len(chart)*40),margin=dict(l=12,r=95,t=15,b=20),template='plotly_white',xaxis_title='EVM votes')
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        headline('Candidate shares')
        st.dataframe(cands[['Candidate','Party','EVM votes','Share %','Station leads']],hide_index=True,use_container_width=True,height=380)
    headline('The four-year record')
    summary=[]
    for y in YEARS:
        m=META[y];s=candidate_summary(y);summary.append({'Year':y,'Election':m['election_type'],'Focus candidate':m['focus'],'Focus party':m['focus_party'],'Focus EVM share (%)':round(100*m['focus_votes']/m['evm_total'],2),'Top vote-getter':s.iloc[0]['Candidate'],'Top-two EVM vote difference':int(s.iloc[0]['EVM votes']-s.iloc[1]['EVM votes'])})
    st.dataframe(pd.DataFrame(summary),hide_index=True,use_container_width=True)
    foot('The official final winning margins can differ from the station-level EVM differences because final declared results also account for postal ballots and administrative reconciliation.')

elif page=='Booth Intelligence':
    hero('Booth Intelligence','Every plotted dot is one actual polling station. Explore any candidate, inspect Q1/median/Q3, compare share against signed margin, and filter the underlying Form 20 rows.')
    x,y=st.columns([1,2])
    with x:year=st.selectbox('Election year',YEARS,index=0,key='booth_year')
    cands=META[year]['candidates']
    with y:idx=st.selectbox('Candidate (reference nominee first)',options=range(len(cands)),format_func=lambda x:choose_label(cands[x]),key=f'booth_candidate_{year}')
    year_note(year)
    df,(q1,med,q3)=candidate_frame(year,idx)
    valid=df.dropna(subset=['focus_share'])
    a,b,c,d=st.columns(4)
    a.metric('Selected candidate EVM votes',fnum(df['votes'].sum()))
    b.metric('Constituency EVM share',fpct(100*df['votes'].sum()/df['evm_votes'].sum()))
    c.metric('Polling-station leads',f"{int(df['is_lead'].sum())} / {len(valid)}")
    d.metric('Median station vote share',fpct(med))
    headline('Vote-share distribution · quartile view')
    l,r=st.columns([1.35,1])
    with l:
        st.plotly_chart(distribution_plot(valid),use_container_width=True)
    with r:
        st.markdown('**Distribution-derived cutoffs**')
        a,b,c=st.columns(3)
        a.metric('Q1',fpct(q1));b.metric('Median',fpct(med));c.metric('Q3',fpct(q3))
        bands=valid.groupby('share_band').agg(Stations=('station','count'),Avg_share=('focus_share','mean'),Avg_margin=('signed_margin_pp','mean')).reindex(['Low','Middle','High']).reset_index().rename(columns={'share_band':'Group','Avg_share':'Avg share %','Avg_margin':'Avg margin pp'})
        st.dataframe(bands.round(2),hide_index=True,use_container_width=True)
        st.caption('Low: share below Q1 · Middle: Q1 through Q3 · High: above Q3. High is relative to this election, not an outright station lead.')
    with st.expander('Interpret these distributions',expanded=True):
        under5=int((valid['focus_share']<5).sum());over= int((valid['share_band']=='High').sum());leaders=int((valid['share_band'].eq('High') & valid['is_lead']).sum())
        st.markdown(f'**{under5:,} of {len(valid):,} stations ({under5/len(valid)*100:.1f}%)** had less than 5% vote share for this candidate. In the High-share quartile, the candidate led **{leaders:,} of {over:,}** stations. The median signed margin across all stations was **{valid["signed_margin_pp"].median():+.2f} pp**. This describes the historical distribution; it does not explain individual voter motives or establish 2027 support.')
    headline('Vote share vs signed margin · proper scatterplot')
    st.plotly_chart(scatter_plot(valid,cands[idx]['name']),use_container_width=True)
    foot('X = candidate votes ÷ all station EVM votes incl. NOTA ×100. Y = (candidate votes − highest competing candidate votes) ÷ EVM votes ×100. No artificial connecting lines. One dot per valid station.')
    headline('Vote share × vote margin matrix')
    st.plotly_chart(matrix_fig(valid)[0],use_container_width=True)
    _,table=matrix_fig(valid)
    a,b=st.columns([1.4,1])
    with a:st.dataframe(table.assign(Total=table.sum(axis=1)),use_container_width=True)
    with b:
        highest=valid[valid['share_band']=='High'];count_leads=int(highest['is_lead'].sum())
        st.markdown('**How to explain this matrix**')
        st.write(f'The High band contains {len(highest)} stations. The selected candidate led at {count_leads} and did not lead at {len(highest)-count_leads}. Every cell is a count of stations, not a vote total.')
        st.caption('Signed-margin bins: large deficit below −20 pp; moderate −20 to −5; narrow −5 to 0; tie; narrow lead 0 to +5; moderate +5 to +20; large above +20.')
    headline('Station-level register · searchable and exportable')
    f1,f2,f3=st.columns([1.6,1,1])
    with f1:search=st.text_input('Find station number or place',placeholder='e.g. Kasna, 38, Mandpa',key=f'search_{year}')
    with f2:share_filter=st.multiselect('Share quartile',['Low','Middle','High','No EVM data'],default=['Low','Middle','High','No EVM data'],key=f'quart_{year}')
    with f3:lead_filter=st.selectbox('Outcome',['All stations','Candidate leads','Candidate trails','Ties'],key=f'lead_{year}')
    shown=df[df['share_band'].isin(share_filter)].copy()
    if search:
        textsearch=search.strip();shown=shown[shown['station'].astype(str).str.contains(re.escape(textsearch),case=False,regex=True)|shown['location'].astype(str).str.contains(re.escape(textsearch),case=False,regex=True)]
    if lead_filter=='Candidate leads':shown=shown[shown['signed_margin_pp']>0]
    elif lead_filter=='Candidate trails':shown=shown[shown['signed_margin_pp']<0]
    elif lead_filter=='Ties':shown=shown[shown['signed_margin_pp']==0]
    display=shown[['station','location','electors','evm_votes','votes','focus_share','strongest_rival_votes','signed_margin_pp','station_leader','share_band','margin_band','qa_diff']].rename(columns={'station':'PS #','location':'Station / location','electors':'Electors','evm_votes':'EVM incl NOTA','votes':'Candidate votes','focus_share':'Vote share %','strongest_rival_votes':'Top rival votes','signed_margin_pp':'Margin pp','station_leader':'Station leader','share_band':'Share quartile','margin_band':'Margin class','qa_diff':'Row QA diff'})
    st.caption(f'{len(display):,} station records matching filters. Quartile thresholds remain based on the full election, not filtered rows.')
    st.dataframe(display,hide_index=True,use_container_width=True,height=430,column_config={'Vote share %':st.column_config.NumberColumn(format='%.2f%%'),'Margin pp':st.column_config.NumberColumn(format='%+.2f pp'),'Electors':st.column_config.NumberColumn(format='%d')})
    st.download_button('Download selected booth data (CSV)',data=display.to_csv(index=False).encode('utf-8-sig'),file_name=f'Jewar_{year}_{cands[idx]["name"].replace(" ","_")}_booths.csv',mime='text/csv')
    if int((df['evm_votes']==0).sum()):note(f"{int((df['evm_votes']==0).sum())} station(s) have zero recorded EVM votes; excluded from percentage plots and distributions, retained in the raw register.",True)

elif page=='Candidate Landscape':
    hero('Candidate Landscape','Candidate-by-candidate EVM totals, polling-station leads and the relationship between constituency shares and station-level results.')
    year=st.selectbox('Election',YEARS,index=0,key='candidate_year')
    year_note(year)
    c=candidate_summary(year)
    l,r=st.columns(2)
    with l:
        headline('Votes by candidate')
        v=c.head(10).sort_values('EVM votes')
        fig=go.Figure(go.Bar(x=v['EVM votes'],y=v['Candidate'],orientation='h',marker_color=[COLORS.get(p,'#8498a4') for p in v['Party']],text=v['EVM votes'],textposition='outside',cliponaxis=False))
        fig.update_layout(height=410,template='plotly_white',margin=dict(l=10,r=86,t=15,b=20));st.plotly_chart(fig,use_container_width=True)
    with r:
        headline('Stations with outright leads')
        v=c[c['Station leads']>0].sort_values('Station leads')
        fig=go.Figure(go.Bar(x=v['Station leads'],y=v['Candidate'],orientation='h',marker_color=[COLORS.get(p,'#8498a4') for p in v['Party']],text=v['Station leads'],textposition='outside',cliponaxis=False))
        fig.update_layout(height=410,template='plotly_white',margin=dict(l=10,r=60,t=15,b=20));st.plotly_chart(fig,use_container_width=True)
    headline('Complete candidate record')
    st.dataframe(c.drop(columns=['Focus']),hide_index=True,use_container_width=True)
    note('Station leads count where a candidate received strictly more votes than every other candidate at that polling station; tied leads are excluded from this measure. Station leads are NOT village-level victories.')
    st.download_button('Download candidate scorecard',c.to_csv(index=False).encode('utf-8-sig'),file_name=f'Jewar_{year}_candidate_scorecard.csv',mime='text/csv')

elif page=='Cross-Year Lens':
    hero('Cross-Year Lens','Track descriptive changes in election returns. Keep candidate identity, alliance structure, election type and polling-station boundaries in view.')
    rows=[]
    for year in YEARS:
        m=META[year];cs=candidate_summary(year)
        rows.append({'Year':year,'Election type':m['election_type'],'Reference candidate':m['focus'],'Party':m['focus_party'],'Reference votes':m['focus_votes'],'Reference EVM share':round(m['focus_votes']/m['evm_total']*100,2),'Station leads':m['focus_station_leads'],'BJP EVM share':float(cs[cs['Party']=='BJP']['Share %'].sum()),'BSP EVM share':float(cs[cs['Party']=='BSP']['Share %'].sum()),'Station count':m['stations']})
    cross=pd.DataFrame(rows)
    st.dataframe(cross,hide_index=True,use_container_width=True)
    a,b=st.columns(2)
    for years_to_show,col,title in [([2017,2022],a,'Assembly elections only'),([2019,2024],b,'Parliamentary Jewar segment only')]:
        with col:
            headline(title)
            selected=cross[cross['Year'].isin(years_to_show)]
            fig=go.Figure()
            for metric,color in [('BJP EVM share','#d88e3c'),('BSP EVM share','#537db4'),('Reference EVM share','#168d8a')]:
                fig.add_trace(go.Bar(name=metric.replace(' EVM share',''),x=selected['Year'].astype(str),y=selected[metric],marker_color=color))
            fig.update_layout(height=345,barmode='group',template='plotly_white',margin=dict(l=12,r=15,t=15,b=22),yaxis_title='% of EVM incl NOTA',legend=dict(orientation='h',y=-.25),xaxis_title='Election')
            st.plotly_chart(fig,use_container_width=True)
    note('<b>Do not interpret these as continuous support for Narender Nagar.</b> The “Reference” bar follows the relevant nominee in each election: 2017 Nagar (SP), 2019 Satveer (BSP alliance), 2022 Bhadana (RLD alliance), and 2024 Mahendra Singh Nagar (SP). The reference line is not a single person or party series.',True)
    headline('Why a naïve booth-to-booth swing is invalid')
    st.markdown('''A 2017 polling-station number can correspond to a different area by 2022 or 2024. Even matching school names can conceal split rooms, merged stations, altered elector lists and location spelling changes. **This dashboard does not claim to have a certified cross-year booth crosswalk.** Once official part-level station mapping is obtained, only verified matches should be compared.''')
    headline('What we can say with confidence')
    st.markdown('''- **2017 Assembly:** Narender Nagar personally contested for SP and obtained 13,216 EVM votes in the uploaded polling-station sheet.\n- **2019 Lok Sabha:** BSP nominee Satveer was the joint BSP–SP–RLD nominee in this parliamentary seat.\n- **2022 Assembly:** RLD nominee Avtar Singh Bhadana contested Jewar under the SP–RLD alliance.\n- **2024 Lok Sabha:** SP nominee Dr. Mahendra Singh Nagar contested the parliamentary race; he is not Narender Nagar.\n\nHistorical results can support factual research and transparent monitoring, but cannot by themselves establish why voters behaved as they did or forecast a future result.''')

elif page=='Issues & Timeline':
    hero('Issues & Development Timeline','Public affairs research linked to dated articles and administrative documents. Political claims, reported experiences and official decisions should be distinguished.')
    t=load_aux('issues.csv').copy()
    categories=sorted(t['topic'].unique().tolist())
    a,b=st.columns([2,1])
    with a:selected=st.multiselect('Topics',categories,default=categories)
    with b:period=st.selectbox('Period',['All years','2017–2019','2020–2022','2023–2024','2025–2026'])
    visible=t[t['topic'].isin(selected)].copy()
    if period!='All years':
        lo,hi=map(int,period.split('–'));visible=visible[pd.to_datetime(visible['date'],errors='coerce').dt.year.between(lo,hi)]
    st.caption(f'{len(visible)} dated findings. Publication coverage is not a representative sample of all residents or issues.')
    for _,r in visible.iterrows():
        with st.expander(f"{r['date']}  ·  {r['topic']}  ·  {r['publisher']}"):
            st.write(r['finding']); st.caption('Limitation / balancing perspective');st.write(r['caveat'])
            st.caption('What needs independent confirmation');st.write(r['verification'])
            if r['url'] and str(r['url']).startswith('https://'):
                st.markdown(f"[Open original source ↗]({r['url']})")
    st.download_button('Download public-issues evidence register',t.to_csv(index=False).encode('utf-8-sig'),file_name='Jewar_Public_Issues_Sources.csv',mime='text/csv')
    note('2027 is a future election. These are documented historical and contemporary public issues, not claims about their electoral impact or which party will gain from them.')

elif page=='Game Data Lab':
    render_data_lab(META, YEARS, load_year)

elif page=='Diagnostics Lab':
    hero('Historical Diagnostics Lab','Interactive sensitivity checks on *past recorded results*. Change the analytical cutoffs; see how many stations meet them. This is not a 2027 prediction model.')
    a,b=st.columns(2)
    with a:year=st.selectbox('Historical election',YEARS,index=0,key='lab_year')
    with b:idx=st.selectbox('Candidate',options=range(len(META[year]['candidates'])),format_func=lambda x:choose_label(META[year]['candidates'][x]),key=f'lab_candidate_{year}')
    df,_=candidate_frame(year,idx);valid=df.dropna(subset=['focus_share','signed_margin_pp'])
    x,y=st.columns(2)
    with x:share_cut=st.slider('Historical share cutoff (%)',0,100,10,step=1)
    with y:margin_band=st.slider('Near-tie margin range (± percentage points)',1,30,5)
    above=valid['focus_share']>=share_cut
    close=valid['signed_margin_pp'].abs()<=margin_band
    c1,c2,c3=st.columns(3)
    c1.metric('Stations meeting share cutoff',f"{int(above.sum())} / {len(valid)}")
    c2.metric('Within selected margin range',int(close.sum()))
    c3.metric('Both conditions',int((above&close).sum()))
    selected=valid.loc[above&close,['station','location','votes','evm_votes','focus_share','signed_margin_pp']].rename(columns={'station':'PS #','location':'Location','votes':'Candidate votes','evm_votes':'EVM votes','focus_share':'Share %','signed_margin_pp':'Margin pp'})
    st.dataframe(selected,hide_index=True,use_container_width=True)
    st.download_button('Export historical diagnostic subset',selected.to_csv(index=False).encode('utf-8-sig'),file_name=f'Jewar_{year}_diagnostic.csv',mime='text/csv')
    headline('Field Pulse — issue research intake')
    st.markdown('A current public-issue survey is not included in the historical Form 20 files. You can inspect **aggregated, non-identifying** issue-research counts here if the team later collects them lawfully and documents the methodology.')
    sample=pd.DataFrame([{'survey_date':'2026-10-12','issue':'Road access','responses':24,'sample_note':'EXAMPLE ONLY — replace with verified data'},{'survey_date':'2026-10-12','issue':'Land compensation','responses':18,'sample_note':'EXAMPLE ONLY — replace with verified data'}])
    st.download_button('Download aggregate issue-template CSV',sample.head(0).to_csv(index=False).encode('utf-8-sig'),file_name='Jewar_Issue_Survey_Template.csv',mime='text/csv')
    upload=st.file_uploader('Optional: load an aggregated public-issues CSV (no names, phone numbers or personal voting responses)',type=['csv'])
    if upload is not None:
        try:
            inc=pd.read_csv(upload)
            if not {'issue','responses','survey_date'}.issubset(set(inc.columns)):
                st.error('Required columns: issue, responses, survey_date (plus optional sample_note).')
            else:
                inc['responses']=pd.to_numeric(inc['responses'],errors='coerce')
                if inc['responses'].isna().any() or (inc['responses']<0).any():st.error('Responses column must contain nonnegative counts.')
                else:
                    s=inc.groupby('issue',as_index=False)['responses'].sum()
                    st.plotly_chart(px.bar(s,x='issue',y='responses',labels={'issue':'Reported issue category','responses':'Aggregated responses'},color_discrete_sequence=['#168d8a']),use_container_width=True)
                    st.caption('User-uploaded research, not an official or representative population statistic. Interpret only alongside sampling frame, fieldwork dates and methodology.')
        except Exception as exc:st.error(f'Could not read the CSV: {exc}')
    foot('Analytical threshold controls reclassify historical station observations only. They do not estimate election outcomes or individual preferences.')

elif page=='Research & QA':
    hero('Research Library & Data Quality','A candidate-facing dashboard should make its sources and known limitations easy to audit. Review them before interpreting a chart.')
    source_df=load_aux('sources.csv')
    headline('Documented input and reconciliation status')
    checks=[]
    for year in YEARS:
        m=META[year];d=load_year(year)
        checks.append({'Year':year,'Source':m['source'],'Station records':len(d),'EVM sum':int(d['evm_votes'].sum()),'Candidate votes':sum(int(d[c['col']].sum()) for c in m['candidates']),'NOTA':int(d['nota'].sum()),'Row checksum exceptions':int((d['qa_diff']!=0).sum()),'Zero-EVM rows':int((d['evm_votes']==0).sum())})
    st.dataframe(pd.DataFrame(checks),hide_index=True,use_container_width=True)
    note('<b>Known source discrepancies:</b> 2019 candidate-column total is 90 votes below the printed candidate subtotal (source station 1). In 2022, the 419 station EVM vote totals sum to 230,872—324 below the uploaded sheet’s printed EVM subtotal of 231,196. This application uses recomputed station rows and displays these caveats.',True)
    note('<b>2024 geographic limitation:</b> uploaded PDF has polling-station serials but no station names or elector counts. One station has zero EVM votes, so its share and margin are not calculated.')
    headline('Key definitions')
    with st.expander('Vote share, signed margin, quartiles and station leads',expanded=True):
        st.markdown('''**Vote share (%)** = selected candidate’s polling-station EVM votes ÷ all votes recorded at that polling station, including NOTA × 100.\n\n**Signed margin (pp)** = (selected candidate EVM votes − the largest EVM votes received by any competing candidate at the same station) ÷ all recorded station EVM votes × 100. Negative = trailing.\n\n**Q1 / median / Q3** = 25th, 50th and 75th percentiles of the *station-level share distribution* (unweighted by station size).\n\n**Outright station lead** = selected candidate exceeded all competitors’ votes at that polling station (ties excluded).\n\n**Final votes** = may differ from polling-station EVM sums due to postal ballots. All booth charts exclude postal votes from numerators and denominators.\n\n**Cross-year station comparison** = unsafe without a validated electoral-roll part / station-location crosswalk.''')
    headline('Source library')
    year_filter=st.multiselect('Publication/election year',sorted(source_df['year'].astype(str).unique()),default=sorted(source_df['year'].astype(str).unique()))
    s=source_df[source_df['year'].astype(str).isin(year_filter)]
    st.dataframe(s,hide_index=True,use_container_width=True,column_config={'url':st.column_config.LinkColumn('Read source')},height=380)
    st.download_button('Download source library',source_df.to_csv(index=False).encode('utf-8-sig'),file_name='Jewar_Source_Register.csv',mime='text/csv')
    headline('Download raw normalized Form 20')
    year=st.selectbox('Dataset',YEARS,key='qa_year')
    st.download_button('Download full station table',load_year(year).to_csv(index=False).encode('utf-8-sig'),file_name=f'Jewar_{year}_Form20_all_candidates.csv',mime='text/csv')
    foot('Provenance: raw figures are extracted from the user-supplied 17-tab Jewar workbook. Article summaries originate from its dated source library and should be checked at the original links for high-stakes claims.')

elif page=='Meeting Brief':
    hero('Candidate Meeting Brief','A neutral, concise presentation sequence with the facts, source limitations and discovery questions you can use in a conversation with Narender Nagar.')
    sections=[
        ('01 · Confirm the scope','“We have prepared a first historical research base for Jewar AC 63, and we would like to understand the constituency information and public-issue questions you want investigated.”'),
        ('02 · Explain the 2017 personal record','“The official 2017 Form 20 records 13,216 EVM votes for Narender Nagar in 343 station rows, with seven outright station leads. The final declared vote total was 13,239 including postal votes.”'),
        ('03 · Show the analysis method','“We analyse each polling station’s vote share, the margin against the strongest competing candidate, its place in the quartile distribution and the overall lead counts. A high quartile is relative and does not guarantee a station lead.”'),
        ('04 · Explain why later elections are different','“2019 involved the BSP–SP–RLD alliance nominee Satveer; 2022 involved the SP–RLD candidate Avtar Singh Bhadana; and 2024 involved SP parliamentary nominee Dr. Mahendra Singh Nagar. These are not Narender Nagar’s personal results.”'),
        ('05 · Discuss documented public issues','“Our dated research register covers airport development, land acquisition, compensation, rehabilitation and local infrastructure. Each public statement is linked to its source, with claims distinguished from government action.”'),
        ('06 · Describe a possible research assignment','“Saarthi can provide certified station crosswalks, public-service issue tracking, properly documented aggregate surveys, and a periodically updated evidence dashboard, subject to agreed scope and methodology.”'),
        ('07 · Ask what the office needs','“Which information gaps are most important, what official records are already available, who should coordinate with us, and what outputs would make the first assignment useful?”')]
    for title,script in sections:
        with st.expander(title,expanded=(title.startswith('01'))):st.write(script)
    headline('Important numbers to keep at hand')
    x,y,z=st.columns(3);x.metric('2017 Narender EVM votes','13,216');y.metric('2017 SP EVM share','6.25%');z.metric('2017 station leads','7 of 343')
    note('This is a descriptive research briefing—not a projection of 2027 election outcomes or a claim about individual voter intentions.',True)

st.markdown('---')
foot('SAARTHI ELECTORAL LENS · Jewar AC 63 · historical research edition · information current to the uploaded datasets and dated research register · no live electoral polling data')

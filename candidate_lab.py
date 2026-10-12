"""Jewar candidate roster and manually-entered scenario sandbox.

This module never derives forecasts, probabilities, or contemporary support from
historical Form 20 records. It shows transparent historical baselines alongside
optional, user-entered hypothetical percentages.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PALETTE = {
    "BJP":"#d88e3c", "SP":"#bb4e62", "BSP":"#537db4",
    "RLD":"#41957f", "INC":"#67779c", "IND":"#8e98a0",
}


def baseline_roster(meta: dict, station_df: pd.DataFrame) -> list[dict]:
    """Return party-tagged candidate results as percentage of *all* EVM incl NOTA."""
    total = float(station_df['evm_votes'].sum())
    return [
        {
            'id': c['col'], 'name': c['name'], 'party': c['party'],
            'kind': 'Official historical candidate',
            'baseline_votes': int(station_df[c['col']].sum()),
            'baseline_share': float(station_df[c['col']].sum()) / total * 100 if total else 0.0,
            'included': True,
        }
        for c in meta['candidates']
    ]


def scenario_summary(entries: list[dict]) -> dict:
    """Sum provided scenario inputs. Never treat omitted share as transferred votes."""
    selected = [r for r in entries if r['included']]
    allocated = sum(float(r['scenario_share']) for r in selected)
    excluded = sum(float(r['baseline_share']) for r in entries if not r['included'] and r['kind'].startswith('Official'))
    return {
        'included': len(selected),
        'allocated': allocated,
        'unallocated': 100 - allocated,
        'excluded_historical_share': excluded,
        'valid': 0 <= allocated <= 100.00005,
    }


def _card(r: dict, year: int, revision: int, is_extra: bool = False) -> dict:
    key = f'jewarlab_{year}_{revision}_{r["id"]}'
    with st.container(border=True):
        name = r['name']
        party = r['party'] or '—'
        enabled = st.toggle(f"{name} · {party}", value=True, key=key+'_on')
        if is_extra:
            st.caption('New entrant · no historical Form 20 votes assigned')
        else:
            st.caption(f"Historical {year}: {r['baseline_votes']:,} EVM votes · {r['baseline_share']:.2f}%")
        entered = st.number_input(
            'Hypothetical share (%)', min_value=0.0, max_value=100.0,
            step=0.25, value=round(float(r.get('seed_share', r['baseline_share'])), 4),
            format='%.4f', disabled=not enabled, key=key+'_share',
            help='Manually entered assumption. Not a poll result or a prediction.',
        )
    return {**r, 'included': enabled, 'scenario_share': float(entered) if enabled else 0.0}


def _group_cards(data: list[dict], year: int, rev: int) -> list[dict]:
    entries = []
    for i in range(0, len(data), 2):
        cols = st.columns(2, gap='small')
        for col, r in zip(cols, data[i:i+2]):
            with col:
                entries.append(_card(r, year, rev, r['kind'] == 'Added manually'))
    return entries


def _scenario_color(party: str) -> str:
    return PALETTE.get(str(party).upper(), '#7892a2')


def _export_payload(year: int, entries: list[dict], meta: dict) -> dict:
    return {
        'format': 'saarthi-jewar-manual-contest-lab-v1',
        'assembly_constituency': 'Jewar AC 63',
        'reference_election_year': year,
        'reference_election_type': meta['election_type'],
        'exported_on': str(date.today()),
        'disclaimer': 'User-entered hypothetical share entries; NOT polling, historical revisions, or a 2027 forecast.',
        'entries': [
            {k: r[k] for k in ('id','name','party','kind','included','scenario_share')}
            for r in entries
        ],
    }


def _load_imported(year: int, rev: int, upload, base: list[dict]) -> str | None:
    """Import a prior scenario into new, not-yet-instantiated Streamlit widget keys."""
    try:
        blob = json.loads(upload.getvalue().decode('utf-8'))
        if blob.get('format') != 'saarthi-jewar-manual-contest-lab-v1':
            return 'Unsupported scenario file format.'
        if blob.get('reference_election_year') != year:
            return f"This file uses {blob.get('reference_election_year')}; select that reference year first."
        vals = blob.get('entries', [])
        if not isinstance(vals, list) or len(vals) > 45:
            return 'The saved scenario has too many or invalid entries.'
        official = {r['id']:r for r in base}
        new_entries, ids, pairs = [], set(), set()
        for obj in vals:
            if not isinstance(obj,dict):return 'An entry is not valid.'
            id_ = str(obj.get('id',''))
            name = str(obj.get('name','')).strip()[:100]
            party = str(obj.get('party','')).strip()[:60]
            if not id_ or len(id_) > 48 or not id_.replace('_','').isalnum():return 'Candidate ID is invalid.'
            if id_ in ids:return 'Duplicate candidate identifiers in file.'
            ids.add(id_)
            share = float(obj['scenario_share'])
            if not 0 <= share <= 100:return 'All shares must be 0–100%.'
            included = obj.get('included')
            if not isinstance(included,bool):return 'Included flags must be true or false.'
            if id_ not in official:
                if not id_.startswith('extra_') or not name:return 'An original-candidate ID could not be matched.'
                pair=(name.casefold(),party.casefold())
                if pair in pairs:return 'Duplicate added candidate.'
                pairs.add(pair)
                new_entries.append({'id':id_, 'name':name, 'party':party,
                    'kind':'Added manually','baseline_votes':0,'baseline_share':0.0,'seed_share':share})
        # Update into new keys so Streamlit does not forbid modifying active widgets.
        next_rev = rev+1
        st.session_state[f'jewarlab_rev_{year}'] = next_rev
        st.session_state[f'jewarlab_extra_{year}_{next_rev}'] = new_entries
        st.session_state[f'jewarlab_nextid_{year}_{next_rev}'] = max([int(r['id'].split('_')[-1])+1 for r in new_entries if r['id'].split('_')[-1].isdigit()] or [0])
        for obj in vals:
            id_ = str(obj['id'])
            key = f'jewarlab_{year}_{next_rev}_{id_}'
            st.session_state[key+'_on'] = bool(obj['included'])
            st.session_state[key+'_share'] = float(obj['scenario_share'])
        return None
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
        return 'Could not read the scenario file. Please use a JSON exported from this lab.'


def render_data_lab(meta: dict, years: list[int], load_year) -> None:
    st.markdown('''<div class="hero"><small>JEWAR · AC 63 · INTERACTIVE DATA LAB</small>
    <h1>Candidate Pulse &amp; Game Data Lab</h1>
    <p>Turn historical ballot candidates on or off, add a new candidate, and enter your own
    hypothetical share assumptions. Historical Form 20 stays unchanged. The sandbox never
    claims to measure present public opinion or forecast the 2027 result.</p></div>''',
        unsafe_allow_html=True)

    col1,col2=st.columns([2,1])
    with col1:
        year=st.selectbox('Choose historical ballot as starting roster', years,
            index=years.index(2022) if 2022 in years else 0, key='jewarlab_reference_year',
            format_func=lambda x:f'{x} · {meta[x]["election_type"]}')
    with col2:
        st.markdown('<div style="height:1.73rem"></div>',unsafe_allow_html=True)
        reset=st.button('↺ Reset this year’s scenario',use_container_width=True)
    if reset:
        st.session_state[f'jewarlab_rev_{year}']=st.session_state.get(f'jewarlab_rev_{year}',0)+1
        st.rerun()
    revision=st.session_state.get(f'jewarlab_rev_{year}',0)
    orig=baseline_roster(meta[year],load_year(year))
    extra_key=f'jewarlab_extra_{year}_{revision}'
    extras=st.session_state.setdefault(extra_key,[])
    counter_key=f'jewarlab_nextid_{year}_{revision}'
    st.session_state.setdefault(counter_key,max([int(r['id'].split('_')[-1])+1 for r in extras if r['id'].split('_')[-1].isdigit()] or [0]))
    st.info(f"**Historical reference:** {year} {meta[year]['election_type']}. {meta[year]['alliance']} ")
    st.caption('Historical ballot names and parties below apply to the selected year only. Added names are hypothetical entrants; this does not confirm anyone’s future nomination.')

    # Import is placed BEFORE the editable widgets, so loading can reset keys safely.
    with st.expander('Load a previously saved scenario (optional)'):
        uploaded=st.file_uploader('Select exported scenario JSON',type=['json'],key=f'jewarlab_import_{year}_{revision}')
        if uploaded is not None and st.button('Load this scenario',key=f'jewarlab_load_{year}_{revision}'):
            err=_load_imported(year,revision,uploaded,orig)
            if err:st.error(err)
            else:st.rerun()

    st.subheader('1 · Select candidates on the ballot')
    st.caption('Switch OFF excludes a candidate from your hypothetical roster. Their historical votes do NOT automatically transfer to other candidates.')
    entries=_group_cards(orig[:4],year,revision)
    if len(orig)>4:
        with st.expander(f'Show remaining {len(orig)-4} historical candidates',expanded=False):
            entries.extend(_group_cards(orig[4:],year,revision))
    st.subheader('2 · Add candidates of your choice')
    if len(extras)>=16:
        st.warning('Maximum 16 additional candidates in one scenario.')
    else:
        with st.form(f'jewarlab_add_form_{year}_{revision}',clear_on_submit=True):
            one,two,three=st.columns([2.2,1.2,1])
            with one:name=st.text_input('Candidate name',placeholder='e.g. New candidate',max_chars=100)
            with two:party=st.text_input('Party / Independent',placeholder='e.g. IND',max_chars=60)
            with three:share=st.number_input('Initial share %',min_value=0.0,max_value=100.0,value=0.0,step=0.25,format='%.2f')
            add=st.form_submit_button('＋ Add candidate')
        if add:
            nm=name.strip();pt=party.strip() or 'IND'
            used={(r['name'].casefold(),r['party'].casefold()) for r in orig+extras}
            if not nm:st.error('Enter a candidate name first.')
            elif (nm.casefold(),pt.casefold()) in used:st.error('This name and party already exist in this roster.')
            else:
                uid=f'extra_{year}_{st.session_state[counter_key]}'
                st.session_state[counter_key]+=1
                extras.append({'id':uid,'name':nm,'party':pt,'kind':'Added manually',
                    'baseline_votes':0,'baseline_share':0.0,'seed_share':float(share)})
                st.session_state[extra_key]=extras
                st.rerun()
    if extras:
        st.caption('Added names are private scenario entries in this browser session. Export JSON to save and reload them later.')
        entries.extend(_group_cards(extras,year,revision))
        with st.expander('Remove a manually added candidate'):
            remove_options={f'{r["name"]} · {r["party"]} [{r["id"]}]':r['id'] for r in extras}
            key=st.selectbox('Choose added candidate',list(remove_options),key=f'jewarlab_remove_option_{year}_{revision}')
            if st.button('Remove selected candidate',key=f'jewarlab_remove_{year}_{revision}'):
                st.session_state[extra_key]=[x for x in extras if x['id']!=remove_options[key]]
                st.rerun()

    stats=scenario_summary(entries)
    st.subheader('3 · Hypothetical share ledger')
    ca,cb,cc,cd=st.columns(4)
    ca.metric('Names included',stats['included'])
    cb.metric('Manually entered share',f"{stats['allocated']:.2f}%")
    cc.metric('Unallocated / other share',f"{stats['unallocated']:.2f}%")
    cd.metric('Historical share excluded',f"{stats['excluded_historical_share']:.2f}%")
    if not stats['valid']:
        st.error(f"The entered shares exceed 100% by {stats['allocated']-100:.2f} percentage points. Reduce some values before interpreting or exporting this scenario.")
    else:
        st.caption('Unallocated includes NOTA, excluded names and any share not assigned manually. It is NOT automatically reallocated to another candidate.')

    selected=[r for r in entries if r['included']]
    if not selected:
        st.warning('Select at least one candidate to show the share comparison.')
    else:
        table=pd.DataFrame([{
            'Candidate':r['name'],'Party':r['party'],'Source':r['kind'],
            'Historical EVM share %':round(r['baseline_share'],4),
            'Entered hypothetical share %':round(r['scenario_share'],4),
            'Difference (pp)':round(r['scenario_share']-r['baseline_share'],4),
        } for r in selected])
        l,r=st.columns([1.25,1])
        with l:
            fig=go.Figure()
            names=[f"{r['name']} · {r['party']}" for r in selected]
            fig.add_trace(go.Bar(name=f'{year} recorded EVM share',x=names,
                y=[r['baseline_share'] for r in selected],marker_color='#bac8cd'))
            fig.add_trace(go.Bar(name='Your hypothetical input',x=names,
                y=[r['scenario_share'] for r in selected],
                marker_color=[_scenario_color(r['party']) for r in selected]))
            fig.update_layout(barmode='group',height=420,template='plotly_white',
                xaxis_title='Selected historical / added candidates', yaxis_title='Share of votes (%)',
                margin=dict(l=12,r=15,t=18,b=75),legend=dict(orientation='h',y=-.42),
                xaxis=dict(tickangle=-35),yaxis=dict(range=[0,105]))
            st.plotly_chart(fig,use_container_width=True)
        with r:
            st.markdown('**Share comparison (illustrative)**')
            st.dataframe(table,hide_index=True,use_container_width=True,height=360)
            st.caption('Changes are differences between user assumptions and the historical baseline, not measured electoral swing. New names have no historical baseline.')
        if stats['valid']:
            fig2=go.Figure()
            for row in selected:
                if row['scenario_share']>0:
                    fig2.add_trace(go.Bar(x=[row['scenario_share']],y=['Manual scenario'],orientation='h',
                        name=f"{row['name']} · {row['party']}",marker_color=_scenario_color(row['party']),
                        hovertemplate='%{x:.2f}%<extra>'+row['name']+'</extra>'))
            if stats['unallocated']>.00005:
                fig2.add_trace(go.Bar(x=[stats['unallocated']],y=['Manual scenario'],orientation='h',
                    name='Unallocated / other',marker_color='#d4dadf',hovertemplate='%{x:.2f}%<extra>Not assigned</extra>'))
            fig2.update_layout(height=175,barmode='stack',template='plotly_white',
                xaxis=dict(title='Manually entered shares (%)',range=[0,100]),
                yaxis=dict(showticklabels=False),margin=dict(l=15,r=15,t=15,b=35),
                legend=dict(orientation='h',y=-.6),showlegend=True)
            st.plotly_chart(fig2,use_container_width=True)

        with st.expander('Optional: view a simple arithmetic combination of selected shares'):
            picked=st.multiselect('Choose entries to sum (no vote-transfer assumption)',
                options=[rr['id'] for rr in selected],format_func=lambda rid: next(f"{r['name']} · {r['party']}" for r in selected if r['id']==rid),
                key=f'jewarlab_combined_{year}_{revision}')
            if picked:
                st.metric('Sum of entered share values',f"{sum(r['scenario_share'] for r in selected if r['id'] in picked):.2f}%")
                st.caption('Arithmetic sum only. It does not model alliance behavior, real vote transfer, or an election result.')

    st.subheader('4 · Export your candidate scenario')
    if stats['valid']:
        payload=_export_payload(year,entries,meta[year]);stamp=f'Jewar_AC63_{year}_Manual_Candidate_Scenario'
        left,right=st.columns(2)
        with left:
            st.download_button('Download editable scenario (JSON)',json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8'),
                file_name=stamp+'.json',mime='application/json',use_container_width=True)
        with right:
            csv=pd.DataFrame([{'Reference year':year,'Candidate':r['name'],'Party':r['party'],
                'Type':r['kind'],'Included':r['included'],
                'Historical share %':round(r['baseline_share'],4),
                'Manual hypothetical share %':round(r['scenario_share'],4)} for r in entries])
            st.download_button('Download share ledger (CSV)',csv.to_csv(index=False).encode('utf-8-sig'),
                file_name=stamp+'.csv',mime='text/csv',use_container_width=True)
    else:
        st.info('Fix the total above 100% to activate scenario exports.')
    st.warning('**Interpretation boundary:** Historical candidates and shares come from uploaded Form 20 records. Every edited share or additional candidate is a manually constructed hypothetical, not field polling, a 2027 vote estimate, an electability assessment or a forecast. No votes are presumed to shift when candidates are excluded.')

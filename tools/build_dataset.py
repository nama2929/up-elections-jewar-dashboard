"""Prepare a self-contained dashboard data package from the audited Jewar research workbook.
Uses Python's standard library to read XLSX XML; never mutates the source.
"""
from pathlib import Path
from zipfile import ZipFile
import csv, json, re, xml.etree.ElementTree as ET
SRC = Path(__file__).resolve().parents[1]/'sources'/'Jewar_Electoral_Research_Quartiles_Margins_Matrix_Enhanced.xlsx'
DEST = Path(__file__).resolve().parents[1]/'data'
DEST.mkdir(exist_ok=True)
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
YEARS={2017:2,2019:3,2022:4,2024:5}
DETAILS={
 2017:dict(election_type='Assembly',focus='Narender Nagar',focus_party='SP',alliance='SP–INC alliance; Narender Nagar contested Jewar on the SP symbol.',source='63- jewar 2017 form 20.xls',source_note='2017 EVM-only totals, exclude postal ballots.'),
 2019:dict(election_type='Lok Sabha segment',focus='Satveer',focus_party='BSP',alliance='BSP–SP–RLD alliance; Satveer contested on BSP symbol. NOT Narender Nagar votes.',source='63- 2019 form 20 data.xls',source_note='2019 station-1 printed candidate subtotal is 90 higher than summed candidate columns.'),
 2022:dict(election_type='Assembly',focus='Avtar Singh Bhadana',focus_party='RLD',alliance='SP–RLD alliance; Avtar Singh Bhadana contested Jewar on the RLD symbol. NOT Narender Nagar votes.',source='AC63- form 20 jewar 2022.xls',source_note='2022 sum of 419 station-level EVM votes is 324 lower than spreadsheet’s printed subtotal.'),
 2024:dict(election_type='Lok Sabha segment',focus='Dr. Mahendra Singh Nagar',focus_party='SP',alliance='SP–INC INDIA alliance; Dr. Mahendra Singh Nagar contested the Lok Sabha election. Different person from Narender Nagar.',source='form 20 data 2024.pdf',source_note='2024 contains no station names/elector counts in uploaded Form 20; one row has zero EVM votes.'),
}
PARTY_MAP={'Bharatiya Janata Party':'BJP','Rashtriya Lok Dal':'RLD','Bahujan Samaj Party':'BSP','Indian National Congress':'INC','Aam Aadmi Party':'AAP','Independent':'IND','IN':'IND','RS':'RPSN'}

def colid(addr):
    letters=re.match(r'[A-Z]+',addr).group();n=0
    for c in letters:n=n*26+ord(c)-64
    return n

def rows_for(z, sheetno):
    root=ET.fromstring(z.read(f'xl/worksheets/sheet{sheetno}.xml'))
    d=root.find(NS+'sheetData')
    out={}
    for row in d.findall(NS+'row'):
        vals={}
        for c in row.findall(NS+'c'):
            loc=c.get('r'); n=colid(loc)
            v=c.find(NS+'v'); inline=c.find(NS+'is')
            s=v.text if v is not None else ''.join(inline.itertext()) if inline is not None else ''
            vals[n]=s or ''
        out[int(row.get('r'))]=vals
    return out

def candidate_metadata(header):
    m=re.match(r'^(.*?)\s*\(([^()]*)\)$',header)
    if m:
        name,party=m.group(1).strip(),m.group(2).strip()
    else:name,party=header.strip(),'UNKNOWN'
    return {'name':name.title() if name.isupper() else name,'party':PARTY_MAP.get(party,party),'source_label':header}

def write_dicts(filename,records,fields):
    with (DEST/filename).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)

with ZipFile(SRC) as z:
    for year,sheetno in YEARS.items():
        rows=rows_for(z,sheetno)
        head=rows[8]
        end=next(k for k in range(8,max(head)+1) if str(head.get(k,'')).strip().lower()=='focus share %')
        candidates=[]
        for i,k in enumerate(range(8,end)):
            c=candidate_metadata(head[k]);c['col']='V'+str(i);c['is_focus']=i==0
            candidates.append(c)
        vals=[]
        for row_i in sorted(rows):
            if row_i<9:continue
            cell=rows[row_i]
            if not str(cell.get(1,'')).strip().isdigit(): continue
            r={'station':int(cell[1]),'location':cell.get(2,''),'electors':cell.get(3,''),'evm_votes':int(float(cell[4] or 0)),'nota':int(float(cell[6] or 0))}
            r.update({c['col']:int(float(cell.get(8+i) or 0)) for i,c in enumerate(candidates)})
            r['qa_diff']=r['evm_votes']-r['nota']-sum(r[c['col']] for c in candidates)
            vals.append(r)
        fields=['station','location','electors','evm_votes','nota']+[c['col'] for c in candidates]+['qa_diff']
        write_dicts(f'form20_{year}.csv',vals,fields)
        detail=DETAILS[year];detail.update({'year':year,'candidates':candidates,'stations':len(vals),'evm_total':sum(r['evm_votes'] for r in vals),'focus_votes':sum(r['V0'] for r in vals),'focus_station_leads':sum(int(r['V0']>max(r[c['col']] for c in candidates[1:])) for r in vals),'invalid_station_rows':sum(r['qa_diff']!=0 for r in vals),'zero_evm_rows':sum(r['evm_votes']==0 for r in vals)})
        print(year,detail['stations'],'evm',detail['evm_total'],'focus',detail['focus_votes'],'leads',detail['focus_station_leads'],'bad_rows',detail['invalid_station_rows'],'zeros',detail['zero_evm_rows'])
    ir=rows_for(z,15);issues=[]
    for idx in sorted(ir):
        if idx<8 or not ir[idx].get(1):continue
        if not re.match(r'^\d{4}-',str(ir[idx].get(1,''))):continue
        row=ir[idx]
        issues.append(dict(date=row.get(1,''),topic=row.get(2,''),publisher=row.get(3,''),finding=row.get(4,''),caveat=row.get(5,''),verification=row.get(6,''),research=row.get(7,''),url=row.get(8,'')))
    write_dicts('issues.csv',issues,['date','topic','publisher','finding','caveat','verification','research','url'])
    sources=[]
    sr=rows_for(z,16)
    for idx in sorted(sr):
        if idx<7 or not sr[idx].get(1):continue
        row=sr[idx]
        if not re.match(r'^20\d{2}',str(row.get(1,''))):continue
        sources.append(dict(year=row.get(1,''),category=row.get(2,''),published=row.get(3,''),publisher=row.get(4,''),note=row.get(5,''),url=row.get(6,'')))
    write_dicts('sources.csv',sources,['year','category','published','publisher','note','url'])
(DEST/'metadata.json').write_text(json.dumps(DETAILS,ensure_ascii=False,indent=2),encoding='utf-8')
print('issues',len(issues),'sources',len(sources))

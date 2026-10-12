from pathlib import Path
import csv,json
P=Path(__file__).resolve().parents[1]/'data'
m=json.loads((P/'metadata.json').read_text(encoding='utf-8'))
expected={2017:(343,211292,13216,7),2019:(388,216782,101005,175),2022:(419,230872,60696,89),2024:(398,203537,31228,27)}
for y,(n,turnout,focus,leads) in expected.items():
    with (P/f'form20_{y}.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    cols=[c['col'] for c in m[str(y)]['candidates']]
    assert len(rows)==n,(y,'station count')
    assert sum(int(r['evm_votes']) for r in rows)==turnout,(y,'EVM votes')
    assert sum(int(r['V0']) for r in rows)==focus,(y,'focus candidate votes')
    assert sum(int(r['V0'])>max(int(r[c]) for c in cols[1:]) for r in rows)==leads,(y,'station leads')
    assert all(sum(int(r[c]) for c in cols)+int(r['nota'])==int(r['evm_votes']) for r in rows),(y,'row checksum')
    print(y,'PASS',n,'stations',turnout,'EVM',focus,'focus votes',leads,'focus leads')
print('All four dataset checks passed.')

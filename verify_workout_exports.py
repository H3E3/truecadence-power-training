from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from services.workout_export import estimate_tss_from_blocks, workout_blocks_for_item, workout_exports_for_item
from training_plan_rules import build_week_plan

ftp = 250
rows, theme, desc, src = build_week_plan(
    phase='build', wk=3, ftp=ftp, hours=12.9, readiness_factor=1,
    intensity_cap='normal', selected_training_days=['周二','周三','周五','周六','周日'],
    preferred_long_day='周日', no_hard_days=[])

exports = []
for item in rows:
    exp = workout_exports_for_item(3, item, ftp)
    if exp:
        exports.append(exp)

# Regression: visible interval title must match exported blocks/TSS.
sweet_12 = {"day": "周二", "kind": "sweet", "name": "甜区适应 3×12min", "detail": "0.90 IF", "dur_h": 1.2, "rest": False}
sweet_15 = {"day": "周二", "kind": "sweet", "name": "甜区容量 3×15min", "detail": "0.90 IF", "dur_h": 1.5, "rest": False}
blocks_12 = workout_blocks_for_item(sweet_12)
blocks_15 = workout_blocks_for_item(sweet_15)
assert sum(block[0] for block in blocks_12 if abs(block[1] - 0.90) < 1e-9) == 3 * 12 * 60, blocks_12
assert sum(block[0] for block in blocks_15 if abs(block[1] - 0.90) < 1e-9) == 3 * 15 * 60, blocks_15
assert estimate_tss_from_blocks(blocks_15) > estimate_tss_from_blocks(blocks_12), (blocks_12, blocks_15)

# Regression: cadence-focused workouts should not export as featureless steady Z2.
cadence_item = {"day": "周三", "kind": "z2", "name": "Z2 + 高踏频唤醒", "detail": "Z2 中加入 6×1min 高踏频", "dur_h": 1.0, "rest": False}
cadence_exp = workout_exports_for_item(1, cadence_item, ftp)
assert cadence_exp and 'Cadence="105"' in cadence_exp['zwo'][1], cadence_exp['zwo'][1]
assert cadence_exp['zwo'][1].count('Cadence="105"') == 6, cadence_exp['zwo'][1]

# Regression: threshold alternates promised as 30s@120% FTP must survive ZWO export.
lt_alt_item = {
    "day": "周二",
    "kind": "threshold",
    "name": "阈值交替 2×20min",
    "detail": "20min内每2min插入30s@264W,其余回到202-220W;练乳酸清除。",
    "dur_h": 1.7,
    "rest": False,
}
lt_alt_exp = workout_exports_for_item(3, lt_alt_item, 220)
assert lt_alt_exp and 'Duration="30" Power="1.200"' in lt_alt_exp['zwo'][1], lt_alt_exp['zwo'][1]
assert lt_alt_exp['zwo'][1].count('Duration="30" Power="1.200"') == 20, lt_alt_exp['zwo'][1]

# Regression: Intervals.icu ERG importer needs duplicate transition points.
erg_lines = cadence_exp['erg'][1].split('[COURSE DATA]', 1)[1].split('[END COURSE DATA]', 1)[0].strip().splitlines()
assert len(erg_lines) >= 4, cadence_exp['erg'][1]
assert erg_lines[-1] == erg_lines[-2], cadence_exp['erg'][1]

assert exports, 'no exports generated'
for exp in exports:
    zname, zxml = exp['zwo']
    expected_prefix = f"TC_{exp['week']:02d}-"
    assert zname.startswith(expected_prefix), zname
    day_num = {'周一':1,'周二':2,'周三':3,'周四':4,'周五':5,'周六':6,'周日':7}[exp['day']]
    assert f"TC_{exp['week']:02d}-{day_num:02d}_" in zname, zname
    for fmt in ('zwo', 'erg', 'mrc'):
        assert exp[fmt][0].startswith(f"TC_{exp['week']:02d}-{day_num:02d}_"), exp[fmt][0]
    root = ET.fromstring(zxml)
    assert root.tag == 'workout_file', zname
    zwo_title = root.findtext('name') or ''
    assert zwo_title.startswith(f"{exp['week']:02d}-{day_num:02d} {exp['day']} "), zwo_title
    workout = root.find('workout')
    assert workout is not None and len(list(workout)) > 0, zname
    for elem in workout:
        assert elem.tag in {'SteadyState','IntervalsT','Warmup','Cooldown','FreeRide'}, (zname, elem.tag)
        if elem.tag == 'SteadyState':
            dur = int(float(elem.attrib['Duration']))
            power = float(elem.attrib['Power'])
            assert dur >= 1, (zname, dur)
            assert 0.2 <= power <= 1.8, (zname, power)
        if elem.tag == 'Warmup':
            assert float(elem.attrib['PowerLow']) <= float(elem.attrib['PowerHigh']), (zname, elem.attrib)
        if elem.tag == 'Cooldown':
            assert float(elem.attrib['PowerLow']) >= float(elem.attrib['PowerHigh']), (zname, elem.attrib)
    for fmt in ('erg','mrc'):
        fname, content = exp[fmt]
        assert '[COURSE HEADER]' in content and '[COURSE DATA]' in content, fname
        assert f"FILE NAME = {exp['week']:02d}-{day_num:02d} {exp['day']} " in content, fname
        data = content.split('[COURSE DATA]',1)[1].split('[END COURSE DATA]',1)[0].strip().splitlines()
        assert len(data) >= 2, fname
        minutes = []
        for line in data:
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 2:
                minutes.append(float(parts[0]))
        assert minutes == sorted(minutes), fname
        assert minutes[-1] > 0, fname
print(f'OK exports={len(exports)} files={len(exports)*3} theme={theme}')
for exp in exports:
    print(exp['day'], exp['name'], exp['zwo'][0], exp['erg'][0], exp['mrc'][0])

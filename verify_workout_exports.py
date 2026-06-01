from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from services.workout_export import workout_exports_for_item
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

assert exports, 'no exports generated'
for exp in exports:
    zname, zxml = exp['zwo']
    root = ET.fromstring(zxml)
    assert root.tag == 'workout_file', zname
    workout = root.find('workout')
    assert workout is not None and len(list(workout)) > 0, zname
    for elem in workout:
        assert elem.tag in {'SteadyState','IntervalsT','Warmup','Cooldown','FreeRide'}, (zname, elem.tag)
        if elem.tag == 'SteadyState':
            dur = int(float(elem.attrib['Duration']))
            power = float(elem.attrib['Power'])
            assert dur >= 60, (zname, dur)
            assert 0.2 <= power <= 1.8, (zname, power)
    for fmt in ('erg','mrc'):
        fname, content = exp[fmt]
        assert '[COURSE HEADER]' in content and '[COURSE DATA]' in content, fname
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

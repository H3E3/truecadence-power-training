from __future__ import annotations


def estimate_tss_from_blocks(blocks):
    """Estimate exported workout TSS from real power blocks."""
    total = 0.0
    for sec, frac in blocks or []:
        try:
            total += (float(sec) / 3600.0) * (float(frac) ** 2) * 100.0
        except Exception:
            continue
    return int(round(total))


def make_zwo_xml(name, desc, segments):
    return f'''<?xml version="1.0" encoding="UTF-8"?>\n<workout_file>\n  <author>TrueCadence</author>\n  <name>{name}</name>\n  <description>{desc}</description>\n  <sportType>bike</sportType>\n  <workout>\n{segments}\n  </workout>\n</workout_file>\n'''


def _steady(sec, frac):
    return f'    <SteadyState Duration="{max(60,int(sec))}" Power="{frac:.3f}"/>'


def _ramp(sec, low, high):
    return f'    <Warmup Duration="{max(60,int(sec))}" PowerLow="{low:.3f}" PowerHigh="{high:.3f}"/>'


def _cooldown(sec, high, low):
    return f'    <Cooldown Duration="{max(60,int(sec))}" PowerHigh="{high:.3f}" PowerLow="{low:.3f}"/>'


def _intervals(rep, on, off, onp, offp):
    return f'    <IntervalsT Repeat="{rep}" OnDuration="{int(on)}" OffDuration="{int(off)}" OnPower="{onp:.3f}" OffPower="{offp:.3f}"/>'


def workout_blocks_for_item(item):
    """Return expanded workout blocks as (duration_seconds, ftp_fraction)."""
    if item.get('rest') or item.get('dur_h',0) <= 0: return []
    total = int(item['dur_h']*3600); kind = item['kind']; name = item.get('name',''); detail = item.get('detail','')
    z2 = .65; z1 = .45
    label = name + ' ' + detail
    def pad(blocks, fill_power=z2, min_tail=300):
        used = sum(sec for sec, _p in blocks)
        tail = max(0, total - used)
        if tail >= min_tail:
            return blocks + [(tail, fill_power)]
        return blocks
    def trim(blocks):
        out=[]; remain=total
        for sec,p in blocks:
            if remain <= 0: break
            use=min(sec, remain)
            if use >= 30: out.append((use,p))
            remain -= use
        return out
    if '阈值交替' in label:
        interval=[]
        for _ in range(10):
            interval += [(90,.95),(30,1.20)]
        blocks = [(600,z2)] + interval + [(300,z1)] + interval + [(600,z1)]
        return pad(trim(blocks), z2)
    if 'AC-W3' in label or '比赛获胜' in label:
        blocks = [(900,z2)] + [(120,1.30),(180,z1)] * 8 + [(60,1.40),(240,z1)] * 3 + [(600,z1)]
        return pad(trim(blocks), z2)
    if 'VO2/TT模拟' in label or '6×6min' in label:
        blocks = [(900,z2)] + [(360,.99),(240,z1)] * 6 + [(600,z1)]
        return pad(trim(blocks), z2)
    if '甜区+VO2' in label or '甜区+VO2穿插' in label:
        blocks = [(600,z2)] + [(1200,.90),(300,z1)] * 2 + [(180,1.10),(180,z1)] * 4 + [(600,z1)]
        return pad(trim(blocks), z2)
    if '赛前激活' in label and ('30s' in label or '耐力+1min' in label):
        blocks = [(900,z2)] + [(60,1.20),(240,z1)] * 3 + [(30,1.45),(210,z1)] * 3 + [(600,z1)]
        return pad(trim(blocks), z1)
    if '开放式 FTP 感受' in label or '小测试' in label:
        blocks = [(600,z2),(180,.90),(180,z1),(180,1.00),(300,z1),(60,1.10),(300,z1),(600,z1)]
        return pad(trim(blocks), z1)
    if kind in ('z2','fatloss','long','tempo'):
        main_power = .78 if kind == 'tempo' else (.62 if kind == 'fatloss' else z2)
        warm = min(600, max(300, int(total * 0.12)))
        cool = min(600, max(300, int(total * 0.10)))
        remaining = max(0, total - warm - cool)
        blocks = [(warm, .50)]
        if remaining > 3600:
            while remaining > 0:
                use = min(1800, remaining)
                blocks.append((use, main_power))
                remaining -= use
                if remaining > 900:
                    blocks.append((180, .55 if kind != 'tempo' else .60))
                    remaining -= 180
        else:
            blocks.append((remaining, main_power))
        blocks.append((cool, .45))
        return [(sec, p) for sec, p in blocks if sec >= 60]
    if kind == 'recovery':
        warm = min(300, max(180, int(total * 0.15)))
        cool = min(300, max(180, int(total * 0.15)))
        main = max(60, total - warm - cool)
        return [(warm, .40), (main, z1), (cool, .35)]
    if kind == 'sweet':
        blocks = [(600,z2)] + [(900,.90),(300,z1)] * 3 + [(600,z1)]
        return pad(trim(blocks), z2)
    if kind in ('threshold','climb'):
        blocks = [(600,z2)] + [(480,.97 if kind=='threshold' else .95),(240,z1)] * 4 + [(600,z1)]
        return pad(trim(blocks), z2)
    if kind == 'vo2':
        blocks = [(900,z2)] + [(180,1.10),(180,z1)] * 6 + [(15,1.50),(45,z1)] * 8 + [(600,z1)]
        return pad(trim(blocks), z2)
    if kind == 'crit':
        blocks = [(900,z2)] + [(240,.95),(180,z1)] * 5 + [(20,1.35),(100,z1)] * 10 + [(600,z1)]
        return pad(trim(blocks), z2)
    if kind == 'openers':
        blocks = [(600,z2)] + [(300,.95),(300,z1)] * 3 + [(600,z1)]
        return pad(trim(blocks), z1)
    if kind == 'race':
        return [(max(900,total), z2)]
    return [(total, z2)]


def zwo_segments_from_blocks(blocks):
    if len(blocks) >= 3:
        first_sec, first_p = blocks[0]
        last_sec, last_p = blocks[-1]
        middle = blocks[1:-1]
        out = [_ramp(first_sec, min(first_p, .50), max(first_p, .55))]
        out.extend(_steady(sec, frac) for sec, frac in middle if sec >= 60)
        prev_p = middle[-1][1] if middle else first_p
        out.append(_cooldown(last_sec, min(max(prev_p, last_p), 1.20), min(last_p, .50)))
        return "\n".join(out)
    return "\n".join(_steady(sec, frac) for sec, frac in blocks)


def mrc_from_blocks(title, desc, blocks):
    lines = [
        "[COURSE HEADER]",
        "VERSION = 2",
        f"UNITS = ENGLISH",
        f"DESCRIPTION = {desc}",
        f"FILE NAME = {title}.mrc",
        "MINUTES PERCENT",
        "[END COURSE HEADER]",
        "[COURSE DATA]",
    ]
    minute = 0.0
    if blocks:
        lines.append(f"{minute:.2f}\t{round(blocks[0][1]*100)}")
    for sec, frac in blocks:
        minute += sec / 60
        lines.append(f"{minute:.2f}\t{round(frac*100)}")
    lines.append("[END COURSE DATA]")
    return "\n".join(lines) + "\n"


def erg_from_blocks(title, desc, blocks, ftp):
    lines = [
        "[COURSE HEADER]",
        "VERSION = 2",
        "UNITS = ENGLISH",
        f"DESCRIPTION = {desc}",
        f"FILE NAME = {title}.erg",
        "MINUTES WATTS",
        "[END COURSE HEADER]",
        "[COURSE DATA]",
    ]
    minute = 0.0
    if blocks:
        lines.append(f"{minute:.2f}\t{round(blocks[0][1]*ftp)}")
    for sec, frac in blocks:
        minute += sec / 60
        lines.append(f"{minute:.2f}\t{round(frac*ftp)}")
    lines.append("[END COURSE DATA]")
    return "\n".join(lines) + "\n"


def workout_exports_for_item(wk, item, ftp):
    blocks = workout_blocks_for_item(item)
    if not blocks: return None
    safe_day = item['day'].replace('周','D')
    kind = item['kind']
    stem = f"TC_W{wk}_{safe_day}_{kind}"
    title = f"W{wk} {item['day']} {item['name']}"
    desc = item['detail']
    zwo_xml = make_zwo_xml(title, desc, zwo_segments_from_blocks(blocks))
    return {
        "week": wk,
        "day": item['day'],
        "name": item['name'],
        "stem": stem,
        "blocks": blocks,
        "estimated_tss": int(item.get('planned_tss') or estimate_tss_from_blocks(blocks)),
        "zwo": (f"{stem}.zwo", zwo_xml),
        "erg": (f"{stem}.erg", erg_from_blocks(stem, desc, blocks, ftp)),
        "mrc": (f"{stem}.mrc", mrc_from_blocks(stem, desc, blocks)),
    }

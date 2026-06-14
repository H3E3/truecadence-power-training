from __future__ import annotations


def _block_sec_power_cadence(block):
    """Return (seconds, ftp_fraction, cadence_or_none) for 2/3-field blocks."""
    try:
        sec = block[0]
        frac = block[1]
        cadence = block[2] if len(block) >= 3 else None
    except Exception:
        sec, frac, cadence = 0, 0, None
    return sec, frac, cadence


def estimate_tss_from_blocks(blocks):
    """Estimate exported workout TSS from real power blocks."""
    total = 0.0
    for block in blocks or []:
        sec, frac, _cadence = _block_sec_power_cadence(block)
        try:
            total += (float(sec) / 3600.0) * (float(frac) ** 2) * 100.0
        except Exception:
            continue
    return int(round(total))


def make_zwo_xml(name, desc, segments):
    return f'''<?xml version="1.0" encoding="UTF-8"?>\n<workout_file>\n  <author>TrueCadence</author>\n  <name>{name}</name>\n  <description>{desc}</description>\n  <sportType>bike</sportType>\n  <workout>\n{segments}\n  </workout>\n</workout_file>\n'''


def _steady(sec, frac, cadence=None):
    cadence_attr = ""
    if cadence:
        cadence_attr = f' Cadence="{int(cadence)}"'
    # Short on/off efforts such as 30s threshold alternates and 15s VO2 spikes
    # must remain short in ZWO. Forcing every SteadyState to >=60s silently
    # deletes the training promise when paired with zwo_segments_from_blocks.
    return f'    <SteadyState Duration="{max(1,int(sec))}" Power="{frac:.3f}"{cadence_attr}/>'


def _ramp(sec, low, high):
    return f'    <Warmup Duration="{max(60,int(sec))}" PowerLow="{low:.3f}" PowerHigh="{high:.3f}"/>'


def _cooldown(sec, high, low):
    # ZWO cooldown ramps from PowerLow to PowerHigh, same attribute direction as Warmup.
    # For a real cooldown the start should be higher and the end should be lower.
    return f'    <Cooldown Duration="{max(60,int(sec))}" PowerLow="{high:.3f}" PowerHigh="{low:.3f}"/>'


def _intervals(rep, on, off, onp, offp):
    return f'    <IntervalsT Repeat="{rep}" OnDuration="{int(on)}" OffDuration="{int(off)}" OnPower="{onp:.3f}" OffPower="{offp:.3f}"/>'


def _interval_minutes_from_label(label, default_minutes):
    """Best-effort parse of names like 3×12min / 3x15min.

    The UI title is the user's promise; exported blocks and page TSS must follow
    that promise instead of silently using a hard-coded default.
    """
    import re
    m = re.search(r"(?:\d+\s*[×xX]\s*)?(\d{1,2})\s*(?:min|分钟)", label or "")
    if not m:
        return default_minutes
    try:
        minutes = int(m.group(1))
    except Exception:
        return default_minutes
    return minutes if 3 <= minutes <= 30 else default_minutes


def workout_blocks_for_item(item):
    """Return expanded workout blocks as (duration_seconds, ftp_fraction)."""
    if item.get('rest') or item.get('dur_h',0) <= 0: return []
    total = int(item['dur_h']*3600); kind = item['kind']; name = item.get('name',''); detail = item.get('detail','')
    z2 = .65; z1 = .45
    label = name + ' ' + detail
    def pad(blocks, fill_power=z2, min_tail=300):
        used = sum(_block_sec_power_cadence(block)[0] for block in blocks)
        tail = max(0, total - used)
        if tail >= min_tail:
            return blocks + [(tail, fill_power)]
        return blocks
    def trim(blocks):
        out=[]; remain=total
        for block in blocks:
            sec, p, cadence = _block_sec_power_cadence(block)
            if remain <= 0: break
            use=min(sec, remain)
            if use >= 30:
                out.append((use,p,cadence) if cadence else (use,p))
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
        if '高踏频' in label or 'cadence' in label.lower():
            # Make cadence-focused sessions visible in the workout file instead of
            # hiding them inside a generic Z2 steady block. ERG/MRC cannot enforce
            # cadence, but ZWO can carry Cadence attributes and Intervals shows the
            # alternating one-minute blocks clearly.
            blocks = [(warm, .50), (300, .62)]
            remaining = max(0, total - warm - cool - 300)
            for _ in range(6):
                if remaining <= 0: break
                blocks.append((60, .70, 105))
                remaining -= 60
                if remaining <= 0: break
                rec = min(180, remaining)
                blocks.append((rec, .60, 90))
                remaining -= rec
            if remaining > 0:
                blocks.append((remaining, .65, 90))
            blocks.append((cool, .45))
            return [block for block in blocks if _block_sec_power_cadence(block)[0] >= 60]
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
        on_sec = _interval_minutes_from_label(label, 15) * 60
        blocks = [(600,z2)] + [(on_sec,.90),(300,z1)] * 3 + [(600,z1)]
        return pad(trim(blocks), z2)
    if kind in ('threshold','climb'):
        default_on = 10 if kind == 'climb' else 8
        on_sec = _interval_minutes_from_label(label, default_on) * 60
        blocks = [(600,z2)] + [(on_sec,.97 if kind=='threshold' else .95),(240,z1)] * 4 + [(600,z1)]
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
        first_sec, first_p, _first_cadence = _block_sec_power_cadence(blocks[0])
        last_sec, last_p, _last_cadence = _block_sec_power_cadence(blocks[-1])
        middle = blocks[1:-1]
        out = [_ramp(first_sec, min(first_p, .50), max(first_p, .55))]
        for block in middle:
            sec, frac, cadence = _block_sec_power_cadence(block)
            if sec >= 1:
                out.append(_steady(sec, frac, cadence))
        prev_p = _block_sec_power_cadence(middle[-1])[1] if middle else first_p
        out.append(_cooldown(last_sec, min(max(prev_p, last_p), 1.20), min(last_p, .50)))
        return "\n".join(out)
    return "\n".join(_steady(sec, frac, cadence) for sec, frac, cadence in (_block_sec_power_cadence(block) for block in blocks))


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
    for block in blocks:
        sec, frac, _cadence = _block_sec_power_cadence(block)
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
    for block in blocks:
        sec, frac, _cadence = _block_sec_power_cadence(block)
        minute += sec / 60
        # Intervals.icu ERG parser expects two adjacent time/power rows for a
        # step change. Without the duplicate transition point it can report
        # "Missing 2nd data line" near [END COURSE DATA] for Z2/long files.
        lines.append(f"{minute:.2f}\t{round(frac*ftp)}")
        lines.append(f"{minute:.2f}\t{round(frac*ftp)}")
    lines.append("[END COURSE DATA]")
    return "\n".join(lines) + "\n"


def workout_export_day_index(day):
    """Return ISO-like weekday number for Chinese weekday labels used in plan rows."""
    day_order = {
        "周一": 1,
        "周二": 2,
        "周三": 3,
        "周四": 4,
        "周五": 5,
        "周六": 6,
        "周日": 7,
        "星期一": 1,
        "星期二": 2,
        "星期三": 3,
        "星期四": 4,
        "星期五": 5,
        "星期六": 6,
        "星期日": 7,
        "星期天": 7,
    }
    return day_order.get(str(day).strip(), 0)


def workout_export_prefix(wk, item):
    day_num = workout_export_day_index(item.get('day', ''))
    return f"{int(wk):02d}-{day_num:02d}" if day_num else f"{int(wk):02d}-00"


def workout_export_stem(wk, item):
    kind = item['kind']
    return f"TC_{workout_export_prefix(wk, item)}_{kind}"


def workout_exports_for_item(wk, item, ftp):
    blocks = workout_blocks_for_item(item)
    if not blocks: return None
    kind = item['kind']
    prefix = workout_export_prefix(wk, item)
    stem = workout_export_stem(wk, item)
    title = f"{prefix} {item['day']} {item['name']}"
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
        "erg": (f"{stem}.erg", erg_from_blocks(title, desc, blocks, ftp)),
        "mrc": (f"{stem}.mrc", mrc_from_blocks(title, desc, blocks)),
    }

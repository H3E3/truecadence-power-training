"""Static verification for feedback delete/clear regression.

The bug: after deleting current-rider feedback, load_feedback() fell back to
merged feedback_*.json files and resurrected stale rows. Current-rider empty
feedback file must be authoritative.
"""
from __future__ import annotations

from pathlib import Path

app = Path('app.py').read_text(encoding='utf-8')
store = Path('services/feedback_store.py').read_text(encoding='utf-8')
combined = app + "\n" + store

required = [
    'if os.path.exists(p):',
    'return trim_func(data)',
    'save_feedback([])',
    'st.rerun()',
]
for marker in required:
    assert marker in combined, f'missing marker: {marker}'

load_start = store.index('def load_feedback_for_rider(')
load_end = store.index('def save_feedback_for_rider(', load_start)
load_block = store[load_start:load_end]
assert 'if data:' not in load_block, 'load_feedback must not require non-empty data before returning current-rider file'
assert load_block.index('if os.path.exists(p):') < load_block.index('merged = []'), 'current-rider file check must precede fallback'

print('OK feedback delete/clear fallback guard verified')

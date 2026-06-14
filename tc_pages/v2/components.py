from __future__ import annotations


def secondary_nav(items: list[tuple[str, str]], active: str | None = None) -> str:
    """Render V2 second-level menu chips.

    Buttons inside V2 pages should route into these second-level states instead of
    calling old Streamlit page UI directly.
    """
    links = []
    for label, href in items:
        cls = "btn primary" if active == label else "btn secondary"
        links.append(f'<a target="_self" class="{cls}" href="{href}">{label}</a>')
    return f'<div class="actions">{"".join(links)}</div>'


def action_placeholder(title: str, description: str, *, tone: str = "blue") -> str:
    return f'''
    <section class="panel hot">
      <div class="label {tone}">二级功能</div>
      <div class="h1">{title}</div>
      <p class="txt">{description}</p>
    </section>
    '''

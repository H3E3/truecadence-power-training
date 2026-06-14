from __future__ import annotations

from tc_pages.v2.dashboard import render_dashboard_page
from tc_pages.v2.upload import render_upload_page
from tc_pages.v2.plan import render_plan_page
from tc_pages.v2.recovery import render_recovery_page
from tc_pages.v2.fueling import render_fueling_page
from tc_pages.v2.power import render_power_page
from tc_pages.v2.profile import render_profile_page
from tc_pages.v2.help import render_feedback_page, render_help_import_page, render_help_page, render_help_privacy_page, render_help_update_page
from tc_pages.v2.shell import _wrap


def render_v2_page(name: str, profile: dict | None = None, load_rider_profile=None, load_feedback=None, load_profile=None, load_rides=None, load_sleep=None, compute_daily_pmc_func=None):
    """V2 page router.

    Keep this thin. New primary pages go into tc_pages/v2/<page>.py.
    New button/secondary-menu states go into page-specific modules or actions,
    not into this router and not into old Streamlit UI pages.
    """
    if name == "dashboard":
        return render_dashboard_page(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    if name == "upload":
        return render_upload_page(load_feedback=load_feedback, load_profile=load_profile, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    if name == "plan":
        return render_plan_page(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    if name == "recovery":
        return render_recovery_page(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    if name == "fueling":
        return render_fueling_page(load_feedback=load_feedback, load_profile=load_profile, load_rides=load_rides, load_sleep=load_sleep, compute_daily_pmc_func=compute_daily_pmc_func)
    if name == "power":
        return render_power_page()
    if name == "profile":
        return render_profile_page(profile=profile, load_rider_profile=load_rider_profile)
    if name == "help":
        return render_help_page()
    if name == "feedback":
        return render_feedback_page()
    if name == "help_privacy":
        return render_help_privacy_page()
    if name == "help_import":
        return render_help_import_page()
    if name == "help_update":
        return render_help_update_page()
    return _wrap("训练驾驶舱", "训练驾驶舱", "")

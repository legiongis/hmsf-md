import logging
import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from arches.app.models.resource import Resource

from fpan.utils.helpers import get_node_value

logger = logging.getLogger(__name__)

weekday_lookup = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

def get_past_week_report_counts(use_date=None):

    if use_date is None:
        today = datetime.date.today()
    else:
        today = datetime.datetime.strptime(use_date, "%Y-%m-%d").date()
    week_ago = today - datetime.timedelta(days=7)

    count_dict = {}
    past_date = week_ago
    while past_date != today:
        count_dict[past_date] = {"ct": 0, "reports": []}
        past_date = past_date + datetime.timedelta(days=1)

    all_reports = Resource.objects.filter(graph__name="Scout Report")

    start = datetime.datetime.now()

    sites_with_reports_already = []
    for report in all_reports:
        date = get_node_value(report, "Scout Visit Date")
        if date == "":
            continue

        # this split is needed because there are some existing reports with
        # multiple dates (this shouldn't happen though)
        date = date.split(";")[0]
        # strip time info from end of date if necessary
        if len(date) > 10:
            date = date[:10]

        related_site = get_node_value(report, "FMSF Site ID")
        if not related_site:
            continue
        site_uuid = related_site["resourceId"]
        site_res = Resource.objects.get(resourceinstanceid=site_uuid)
        fmsfid = get_node_value(site_res, "FMSF ID")

        report_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        if report_date >= week_ago and report_date < today:

            resid = str(report.resourceinstanceid)

            report_day_of_week = report_date.weekday()
            count_dict[report_date]["ct"] += 1
            count_dict[report_date]["reports"].append({
                "resid": resid,
                "fmsfid": fmsfid,
            })

        else:
            sites_with_reports_already.append(fmsfid)

    for k, v in count_dict.items():
        for report in v['reports']:
            report["new_site"] = report["fmsfid"] in sites_with_reports_already

    logger.info(f"report count generation completed | {datetime.datetime.now() - start} seconds")
    return count_dict


def send_weekly_summary(use_date=None):

    counts = get_past_week_report_counts(use_date=use_date)
    formatted_counts = {}
    total_reports_ct = 0
    new_sites_visited_ct = 0
    for k, v in counts.items():
        dayname = weekday_lookup[k.weekday()]
        weekday_str = f"{dayname} ({k.month}-{k.day})"
        formatted_counts[weekday_str] = v
        total_reports_ct += v["ct"]
        for r in v["reports"]:
            if r["new_site"] is True:
                new_sites_visited_ct += 1

    sdate = list(counts.keys())[0].strftime("%m/%d")
    edate = list(counts.keys())[-1].strftime("%m/%d")
    startend_date_str = f"{sdate} - {edate}"

    # current_site = get_current_site(request)
    msg_vars = {
        'total_reports_ct': total_reports_ct,
        'new_sites_visited_ct': new_sites_visited_ct,
        'count_data': formatted_counts,
        'domain': settings.DEFAULT_FROM_EMAIL.split("@")[1],
    }
    message_txt = render_to_string('reporting/weekly_report_email_text.htm', msg_vars)
    message_html = render_to_string('reporting/weekly_report_email_html.htm', msg_vars)
    subject_line = f"{settings.EMAIL_SUBJECT_PREFIX}- Week of {startend_date_str}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [i[1] for i in settings.FPAN_ADMINS]
    email = EmailMultiAlternatives(subject_line, message_txt, from_email, to=to_emails)
    email.attach_alternative(message_html, "text/html")
    email.send()

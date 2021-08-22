import os
import csv
import uuid
import json
from django.conf import settings
from django.shortcuts import render, HttpResponse
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMultiAlternatives
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_text
from django.template.loader import render_to_string
from django.contrib.auth.models import User

from .statistics_reporting import get_past_week_report_counts
from .helpers import weekday_lookup

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

    current_site = get_current_site(request)
    msg_vars = {
        'total_reports_ct': total_reports_ct,
        'new_sites_visited_ct': new_sites_visited_ct,
        'count_data': formatted_counts,
        'domain': current_site.domain,
    }
    message_txt = render_to_string('email/weekly_report_email_text.htm', msg_vars)
    message_html = render_to_string('email/weekly_report_email_html.htm', msg_vars)
    subject_line = f"{settings.EMAIL_SUBJECT_PREFIX}- Week of {startend_date_str}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_emails = [i[1] for i in settings.FPAN_ADMINS]
    email = EmailMultiAlternatives(subject_line, message_txt, from_email, to=to_emails)
    email.attach_alternative(message_html, "text/html")
    email.send()

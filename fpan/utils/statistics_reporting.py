import datetime
from arches.app.models.resource import Resource

from .helpers import get_node_value, weekday_lookup


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
        # there are multiple dates (this shouldn't happen though)
        date = date.split(";")[0]

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

    print("time elapsed: ", datetime.datetime.now() - start)
    return count_dict

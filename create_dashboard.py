import requests
import click
import json
import validators

PROJECT_NAME = ''
REPORTPORTAL_URL = ''
JOB_NAME = ''
API_TOKEN = ''


HEADERS = {'Content-Type': 'Application/json',
           'Accept': 'application/json',
           'Authorization': 'bearer ' + API_TOKEN}


def get_dashboard_by_id(project_name, dashboard_id):
    url = REPORTPORTAL_URL + '/api/v1/' + project_name + '/dashboard/' + dashboard_id
    return requests.get(url, headers=HEADERS)


def get_widget_by_id(project_name, widget_id):
    url = REPORTPORTAL_URL + '/api/v1/' + project_name + '/widget/' + widget_id
    return requests.get(url, headers=HEADERS)


def get_filter_by_name(project_name, filter_name):
    url = REPORTPORTAL_URL + '/api/v1/' + project_name + '/filter'
    response = requests.get(url, headers=HEADERS)
    for filter in response.json()['content']:
        if filter['name'] == filter_name:
            return filter
    raise Exception("Filter '{}' not found.".format(filter_name))


def get_dashboard_by_name(project_name, dashboard_name):
    url = REPORTPORTAL_URL + '/api/v1/' + project_name + '/dashboard'
    response = requests.get(url, headers=HEADERS)
    for dashboard in response.json():
        if dashboard['name'] == dashboard_name:
            return dashboard
    raise Exception("Dashboard '{}' not found.".format(dashboard_name))


def flaky_tests_cases(filter):
    with open('FLAKY TESTS CASES.json') as json_file:
        widget_json = json.load(json_file)
    widget_json['name'] = "{0} - {1}".format(filter['name'], widget_json['name'])
    widget_json['content_parameters']['widgetOptions']['launchNameFilter'][0] = filter['name']
    widget_json['filter_id'] = ""
    return widget_json


def update_default_widget_json(json_filename, filter):
    with open(json_filename) as json_file:
        widget_json = json.load(json_file)
    widget_json['name'] = "{0} - {1}".format(filter['name'], widget_json['name'])
    widget_json['content_parameters']['widgetOptions']['filterName'][0] = filter['name']
    widget_json['filter_id'] = filter['id']
    return widget_json


def create_widget(project_name, widget_json):
    url = REPORTPORTAL_URL + '/api/v1/' + project_name + '/widget'
    response = requests.post(url, data=json.dumps(widget_json), headers=HEADERS)
    return response


def search_widget(project_name, term):
    url = REPORTPORTAL_URL + '/api/v1/' + project_name + '/widget/shared/search?term=' + term
    response = requests.get(url, headers=HEADERS)
    return response


def update_widget(project_name, widget_id, widget_json):
    url = REPORTPORTAL_URL + "/api/v1/" + project_name + '/widget/' + widget_id
    response = requests.put(url, data=json.dumps(widget_json), headers=HEADERS)
    return response


def update_dashboard(project_name, dashboard_id, widgets_ids: dict):
    with open("DASHBOARD.json", 'r') as json_file:
        dashboard = json.load(json_file)
    print("\tNew Dashboards:")

    index = 0
    for widget_name in widgets_ids:
        widget_id = widgets_ids[widget_name]
        response = get_widget_by_id(PROJECT_NAME, widget_id)
        widget = response.json()
        dashboard['widgets'][index]['widgetId'] = widget['id']
        add_widget_json = {"addWidget": ""}
        add_widget_json['addWidget'] = dashboard['widgets'][index]

        index = index + 1
        url = REPORTPORTAL_URL + "/api/v1/" + project_name + '/dashboard/' + dashboard_id
        response = requests.put(url, data=json.dumps(add_widget_json), headers=HEADERS)
        if response.status_code == 200:
            print("\t\t{\"name\": %s, \"id\": %s}" % (widget['name'], widget['id']))
            print("\t\t%s" % json.dumps(add_widget_json, indent=4, sort_keys=True))
        else:
            raise Exception(response.json())


def validate_url(ctx, param, value):
    if validators.url(value):
        return value
    else:
        raise click.BadParameter("url '{}' is not valid".format(value))


def validate_api_token(ctx, param, value):
    if validators.uuid(value):
        return value
    else:
        raise click.BadParameter("api token '{}' is not valid".format(value))


@click.command()
@click.option('--reportportal-url', required=True, help='ReportPortal URL.', envvar='REPORTPORTAL_URL', callback=validate_url)
@click.option('--api-token', required=True, help='API Token for ReportPortal', envvar='API_TOKEN', callback=validate_api_token)
@click.option('--project-name', required=True, help='Project Name in ReportPortal.', envvar='PROJECT_NAME')
@click.option('--job-name', required=True, help='Job name in Jenkins.', envvar='JOB_NAME')
def main(reportportal_url, api_token, project_name, job_name):
    """Create Dashboard in ReportPortal."""

    global PROJECT_NAME
    global JOB_NAME
    global REPORTPORTAL_URL
    global API_TOKEN
    global HEADERS

    PROJECT_NAME = project_name
    JOB_NAME = job_name
    REPORTPORTAL_URL = reportportal_url
    API_TOKEN = api_token
    HEADERS = {'Content-Type': 'Application/json',
               'Accept': 'application/json',
               'Authorization': 'bearer ' + API_TOKEN}

    dashboard = get_dashboard_by_name(PROJECT_NAME, JOB_NAME)
    filter = get_filter_by_name(PROJECT_NAME, JOB_NAME)

    widgets = {
        'LAUNCH STATISTICS AREA CHART': update_default_widget_json('LAUNCH STATISTICS AREA CHART.json', filter),
        'LAUNCH STATISTICS BAR CHART': update_default_widget_json('LAUNCH STATISTICS BAR CHART.json', filter),
        'INVESTIGATED PERCENTAGE OF LAUNCHES': update_default_widget_json('INVESTIGATED PERCENTAGE OF LAUNCHES.json',                                                                      filter),
        'TEST CASES GROWTH TREND CHART': update_default_widget_json('TEST CASES GROWTH TREND CHART.json', filter),
        'OVERALL STATISTICS PANEL': update_default_widget_json('OVERALL STATISTICS PANEL.json', filter),
        'LAUNCHES DURATION CHART': update_default_widget_json('LAUNCHES DURATION CHART.json', filter),
        'LAUNCH EXECUTION AND ISSUE STATISTICS': update_default_widget_json('LAUNCH EXECUTION AND ISSUE STATISTICS.json',                                                                        filter),
        'FAILED CASES TREND CHART': update_default_widget_json('FAILED CASES TREND CHART.json', filter),
        'LAUNCH TABLE': update_default_widget_json('LAUNCH TABLE.json', filter),
        'FLAKY TESTS CASES': flaky_tests_cases(filter)
    }

    print("%s" % JOB_NAME)
    print("\tWidgets:")
    for widget_name in widgets.keys():
        response = create_widget(PROJECT_NAME, widgets[widget_name])
        if response.status_code == 201:
            widget_id = response.json()["id"]
        elif response.status_code == 409:
            widget_id = search_widget(PROJECT_NAME, widgets[widget_name]['name']).json()['content'][0]['id']
            response = update_widget(PROJECT_NAME, widget_id, widgets[widget_name])

            if response.status_code == 200:
                widgets[widget_name] = widget_id
            else:
                raise Exception(response.json())
        else:
            raise Exception(response.json())
        print("\t\t{\"name\": %s - %s, \"id\": %s}" % (JOB_NAME, widget_name, widget_id))
        widgets[widget_name] = widget_id

    print("\tDashboard:")
    print("\t\t{\"name\": %s, \"id\": %s}" % (JOB_NAME, dashboard['id']))

    update_dashboard(PROJECT_NAME, dashboard['id'], widgets)


if __name__ == '__main__':
    main()

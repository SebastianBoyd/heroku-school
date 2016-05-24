import os
from flask import Flask, request
from flask.ext.cors import CORS, cross_origin
from flask.ext.compress import Compress
import cookielib
import urllib
import urllib2
import re
from bs4 import BeautifulSoup
import json
import decimal

app = Flask(__name__)
app.config.update(
    DEBUG=False,
    PROPAGATE_EXCEPTIONS=False
)
cors = CORS(app)
Compress(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def format_num(num):
    try:
        dec = decimal.Decimal(num)
    except:
        return 'uh_oh'
    tup = dec.as_tuple()
    delta = len(tup.digits) + tup.exponent
    digits = ''.join(str(d) for d in tup.digits)
    if delta <= 0:
        zeros = abs(tup.exponent) - len(tup.digits)
        val = '0.' + ('0'*zeros) + digits
    else:
        val = digits[:delta] + ('0'*tup.exponent) + '.' + digits[delta:]
    val = val.rstrip('0')
    if val[-1] == '.':
        val = val[:-1]
    if tup.sign:
        return '-' + val
    return val

def get_raw_data(username, password):
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        database = '10'
        login_data = urllib.urlencode({'Database' : database, 'LogOnDetails.UserName' : username, 'LogOnDetails.Password' : password})
        opener.open('https://home.tamdistrict.org/HomeAccess/Account/LogOn', login_data, 15)
        if [cookie for cookie in cj if cookie.name == ".AuthCookie"] == []:
            return {}
        resp = opener.open('https://home.tamdistrict.org/HomeAccess/Content/Student/Assignments.aspx', None, 15)
        html = resp.read()
        return html

def get_grades(username, password):
    #html = open('test.html', 'r').read()
    html = get_raw_data(username, password)

    html = html.decode('utf8', 'ignore')
    soup = BeautifulSoup(html)
    charts = soup.find_all('table')
    classes_list = []
    for classroom_soup in soup.find_all("div", { "class" : "AssignmentClass"}):
        class_title = classroom_soup.find_all("div", class_="sg-header sg-header-square")[0].find_all("a")[0].string.strip()
        class_title = re.sub(r'[0-9]{1,5} - [0-9]{1,2} ', ' ', class_title).strip()
        url = urllib.quote_plus(class_title.replace (" ", "_").lower())
        assignment_list = []
        try:
            for tr in classroom_soup.find("table", class_="sg-asp-table").find_all("tr", class_="sg-asp-table-data-row"):
                td = tr.find_all("td")
                due = td[0].string
                assigned = td[1].string
                assigment_title = td[2].find_all("a")[0].string.strip()
                assignment_category = td[3].string.strip()
                score_my = format_num(td[4].string.strip())
                score_total = format_num(td[5].string.strip())
                assignment = {'title':assigment_title, 'category':assignment_category,
                                                'date_assigned':assigned, 'date_due':due,
                                                'score':score_my, 'max_score':score_total}
                assignment_list.append(assignment)
        except:
            continue
        grade_list = []
        for tr in classroom_soup.find("div", class_="sg-view-quick sg-clearfix").find("table", class_="sg-asp-table").find_all("tr", class_="sg-asp-table-data-row"):
            td = tr.find_all("td")
            length = len(td)
            grade_items_docs = ["grade_category", "points", "max_points", "percent", "weight", "weighted_points"]
            grade_items = []
            for t in td:
                grade_items.append(t.string.strip())
            while len(grade_items) < 6:
                grade_items.append('')
            grade = {'category':grade_items[0], 'weight':grade_items[4], 'score':grade_items[1],
                            'max_score':grade_items[2], 'percent':grade_items[3],
                            'weighted_points':grade_items[5]}
            grade_list.append(grade)
        grade_str = classroom_soup.find("span", id=re.compile("plnMain_rptAssigmnetsByCourse_lblOverallAverage_\d")).string
        p = re.compile(r'\(([^\)]+)\)')
        grade_percent = format_num(re.sub(r'\([^)]*\)', '', grade_str).strip())
        try:
            grade_letter = p.search(grade_str).group(1)
        except:
            grade_letter = ''
        classes_list.append({'assignments':assignment_list, 'title':class_title,
                             'grade_table':grade_list, 'grade_percent':grade_percent,
                             'grade_letter':grade_letter, 'url':url})
    response = {'classes': classes_list}
    return json.dumps(response)

@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
    if request.method == 'GET':
        return 'you are using GET, to use this api switch to a POST request'
    if request.method == 'POST':
        print request.form
        if 'login' in request.form and 'password' in request.form:
            return get_grades(request.form['login'], request.form['password'])
        return 'error'


if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

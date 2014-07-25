#!/bin/usr/env python
# -*- coding: utf-8 -*-

import HTMLParser
from math import ceil
from time import sleep
from lxml import html
import requests


entities = HTMLParser.HTMLParser()


def get_url_tree(url):
    sleep(DELAY)
    page = requests.get(url)
    tree = html.fromstring(page.text)
    return tree


def get_num_results(tree):
    summary = tree.xpath("//div[@class='results-summary']/strong/text()")
    num_results = summary[0].split()[0]  # if nums == 'no', no results.
    return int(num_results)


def get_num_pages(num_results):
    num_pages = int(ceil(float(num_results)/20))
    return num_pages


def get_study_ids(tree):
    hrefs = tree.xpath("//td[@style='padding-left:1em; padding-top:2ex']/a")
    ids = [h.attrib['href'].split('/')[-1].split('?')[0] for h in hrefs]
    return ids


def search_ct(search_url):
    results_ids = []
    first_tree = get_url_tree(search_url)
    num_results = get_num_results(first_tree)
    num_pages = get_num_pages(num_results)
    first_ids = get_study_ids(first_tree)
    results_ids += first_ids
    for i in range(2, num_pages + 1):
        next_page_url = search_url + '&pg=' + str(i)
        next_page_tree = get_url_tree(next_page_url)
        next_page_ids = get_study_ids(next_page_tree)
        results_ids += next_page_ids
    return results_ids


def scrape_study(study_id):
    study = {}
    study['id'] = study_id
    url = 'https://clinicaltrials.gov/ct2/show/' + study_id
    study['url'] = url
    tree = get_url_tree(url + '?show_locs=Y#locn')
    content = tree.xpath("//div[@id='main-content']")[0]
    title = content.xpath("//h1/text()")[0]
    study['title'] = entities.unescape(title)
    sponsor = content.xpath(
        "//div[@id='trial-info-1']"
        "/div[@id='sponsor']/text()")[0].strip()
    study['sponsor'] = entities.unescape(sponsor)
    pci_tag = content.xpath(
        "//div[@class='indent1' and @style='margin-top:3ex']"
        "/div[@class='indent2' and @style='margin-top:2ex']")[0]
    purpose_tag = pci_tag.xpath("//div[@class='body3']")[0]
    purpose_lines = []
    for child in purpose_tag.getchildren():
        if child.tag == 'p':
            paragraph = child.text.strip()
            purpose_lines.append(paragraph)
        elif child.tag == 'ul':
            for list_item in child.getchildren():
                purpose_lines.append('  - ' + list_item.text)
    purpose = '\n'.join(purpose_lines)
    study['purpose'] = entities.unescape(purpose)
    ci_tag = pci_tag.xpath(
        "//div[@align='center']/table[@class='data_table']"
        "/tr[@valign='top' and @align='left']")[0]
    cond_tag = ci_tag[0]
    conditions = cond_tag.text_content().split('\r\n')
    conditions = [entities.unescape(c.strip()) for c in conditions if c]
    study['conditions'] = conditions
    try:
        intr_tag = ci_tag[1]
        interventions = intr_tag.text_content().split('\r\n')
        interventions = [entities.unescape(i.strip())
                         for i in interventions if i]
    except IndexError:
        interventions = []
    study['interventions'] = interventions

    def is_country_chile(tr_tag):
        return_value = 0
        for td_tag in tr_tag:
            if ('class', 'header3') in td_tag.attrib.items() and \
                    ('style', 'padding-top:2ex') in td_tag.attrib.items():
                return_value = 1
                if td_tag.text.lower() == 'chile':
                    return_value = 2
        return return_value

    locs_tag = content.xpath(
        "//div[@class='indent1' and @style='margin-top:3ex']"
        "/div[@class='indent2' and @style='margin-top:2ex']"
        "/table[@class='layout_table indent2' and"
        "@summary='Layout table for location information']/tr")
    found_chile = False
    locations = []
    for tr_indx in range(len(locs_tag)):
        if found_chile is False:
            country_val = is_country_chile(locs_tag[tr_indx])
            if country_val == 2:
                found_chile = True
                continue
        else:
            country_val = is_country_chile(locs_tag[tr_indx])
            if country_val == 1:
                break
            else:
                for td_tag in locs_tag[tr_indx]:
                    if ('headers', 'locName') in td_tag.attrib.items():
                        loc_name = '' if td_tag.text is None else td_tag.text
                    if ('headers', 'locStatus') in td_tag.attrib.items():
                        loc_status = '' if td_tag.text is None else td_tag.text
                        loc_place = locs_tag[tr_indx+1].text_content().strip()
                        loc = {'name': entities.unescape(loc_name),
                               'status': entities.unescape(loc_status),
                               'place': entities.unescape(loc_place)}
                        locations.append(loc)
    study['locations'] = locations
    return study


def scrape_all_studies(search_results):
    studies = []
    for result_id in search_results:
        study = scrape_study(result_id)
        studies.append(study)
    return studies


def pprint_study(study_dict):
    print '\n', 'ID:', study_dict['id']
    print '\n', 'URL:', study_dict['url']
    print '\n', 'TITLE:', study_dict['title']
    print '\n', 'SPONSOR:', study_dict['sponsor']
    print '\n', 'PURPOSE:', study_dict['purpose']
    print '\n', 'CONDITIONS:'
    for c in study_dict['conditions']:
        print c
    if len(study_dict['interventions']) == 0:
        print '\n', 'INTERVENTIONS: No interventions.'
    else:
        print '\n', 'INTERVENTIONS:'
        for i in study_dict['interventions']:
            print i
    print '\n', 'LOCATIONS:'
    for l in study_dict['locations']:
        loc_str = ''
        if l['status']:
            loc_str += '[' + l['status'].upper() + '] '
        if l['name']:
            loc_str += l['name'] + '; '
        loc_str += l['place']
        print loc_str


#TODO: get study status too, to see if it changes (closes especially)
#TODO: add 'id': value to study dict.


if __name__ == '__main__':

    DELAY = 1

    #URL = 'https://clinicaltrials.gov/ct2/results?term=heart+attack&cntry1=SA%3ACL'
    URL = 'http://clinicaltrials.gov/ct2/results?term=cancer&recr=Open&rslt=&type=&cond=&intr=&titles=&outc=&spons=&lead=&id=&state1=&cntry1=SA%3ACL&state2=&cntry2=&state3=&cntry3=&locn=&gndr=&rcv_s=&rcv_e=&lup_s=&lup_e='

    results = search_ct(URL)
    studies = scrape_all_studies(results)

    print
    print 'URL:', URL
    print
    print '# RESULTS:', len(studies)
    print
    raw_input('press ENTER')
    for s in studies:
        pprint_study(s)
        raw_input('\npress ENTER')

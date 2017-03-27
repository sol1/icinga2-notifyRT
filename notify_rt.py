#!/usr/bin/python3
'''Icinga2 plugin to create and track RT tickets when services and hosts go critical'''

import os
import re
import json
import syslog
import argparse

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
# Disable unverified SSL warning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

RT_REGEX = re.compile(r'(# Ticket )(\w+)( created)')
TICKETID_REGEX = re.compile(r'(#)([0-9]+)(\])')

CONFIG_FILE = open('/etc/icinga2/scripts/notify_rt.json')
CONFIG = json.loads(CONFIG_FILE.read())

SESSION = requests.session()

PARSER = argparse.ArgumentParser(
    description='Icinga2 plugin to create and track RT tickets when services and hosts go critical')
PARSER.add_argument('host', type=str, help='check hostname')
PARSER.add_argument('state', type=str, help='check state')
PARSER.add_argument('type', type=str, help='notification type')
PARSER.add_argument('--service', dest='service', default="",
                    help='check service name')
PARSER.add_argument('--requestor', dest='requestor', default="",
                    help='email address to set RT ticket requestor as')

ARGS = PARSER.parse_args()


def authenticate_rt(username, password):
    '''Authenticates with the RT server for all subsequent requests'''

    SESSION.post(CONFIG['rt_addr'], data={"user": username, "pass": password})


def create_ticket_rt(subject):
    '''Creates a ticket in RT and returns the ticket ID'''

    additional_output = os.environ['SERVICEOUTPUT'] or os.environ['HOSTOUTPUT']
    state = os.environ['SERVICESTATE'] or os.environ['HOSTSTATE']

    message = "Notification Type: {}\n \n".format(os.environ['NOTIFICATIONTYPE'])
    message += " Service: {}\n".format(os.environ['SERVICEDESC'])
    message += " Host: {}\n".format(os.environ['HOSTALIAS'])
    message += " Address: {}\n".format(os.environ['HOSTADDRESS'])
    message += " State: {}\n \n".format(state)
    message += " Additional Info: {}\n \n".format(additional_output)
    message += " Comment: [{}] {}\n".format(
        os.environ['NOTIF_AUTH_NAME'],
        os.environ['NOTIF_COMMENT'])

    ticket_data = "id: ticket/new\n"
    ticket_data += "Queue: {}\n".format(CONFIG['rt_queue'])
    ticket_data += "Requestor: {}\n".format(ARGS.requestor)
    ticket_data += "Subject: {}\n".format(subject)
    ticket_data += "Text: {}".format(message)

    res = SESSION.post(
        CONFIG['rt_addr'] + "/REST/1.0/ticket/new",
        data={"content": ticket_data},
        headers=dict(Referer=CONFIG['rt_addr']))

    return RT_REGEX.search(res.text).group(2)


def add_comment_rt(ticket_id):
    '''Add a comment to an existing RT ticket'''

    additional_output = os.environ['SERVICEOUTPUT'] or os.environ['HOSTOUTPUT']
    state = os.environ['SERVICESTATE'] or os.environ['HOSTSTATE']

    message = "Notification Type: {}\n \n".format(os.environ['NOTIFICATIONTYPE'])
    message += " Service: {}\n".format(os.environ['SERVICEDESC'])
    message += " Host: {}\n".format(os.environ['HOSTALIAS'])
    message += " Address: {}\n".format(os.environ['HOSTADDRESS'])
    message += " State: {}\n \n".format(state)
    message += " Additional Info: {}\n \n".format(additional_output)
    message += " Comment: [{}] {}\n".format(
        os.environ['NOTIF_AUTH_NAME'],
        os.environ['NOTIF_COMMENT'])

    ticket_data = "id: {id}\n".format(id=ticket_id)
    ticket_data += "Action: comment\n"
    ticket_data += "Text: {text}".format(text=message)

    SESSION.post(
        CONFIG['rt_addr'] + "/REST/1.0/ticket/{id}/comment".format(
            id=ticket_id),
        data={"content": ticket_data},
        headers=dict(Referer=CONFIG['rt_addr']))

    return

def set_status_rt(ticket_id, status="open"):
    '''Set rt ticket status'''

    ticket_data = "Status: {}\n".format(status)

    SESSION.post(
        CONFIG['rt_addr'] + "/REST/1.0/ticket/{id}/edit".format(
            id=ticket_id),
        data={"content": ticket_data},
        headers=dict(Referer=CONFIG['rt_addr']))

    return

def get_comments_icinga(username, password, hostname, servicename):
    '''Get all icinga comments associated with a hostname'''

    filters = 'host.name=="{}"'.format(hostname)
    filters += '&&service.name=="{}"'.format(servicename)
    filters += '&&comment.author=="{}"'.format(username)

    body = {'filter': filters}

    res = SESSION.get(
        CONFIG['icinga_addr'] + "/v1/objects/comments",
        auth=(username, password),
        verify=False,
        json=body)

    result = json.loads(res.text)['results']

    return result

def add_comment_icinga(username, password, hostname, servicename, comment_text):
    '''Create comment on an icinga service or host'''

    filters = 'host.name=="{}"'.format(hostname)
    object_type = 'Host'

    if servicename != "":
        object_type = 'Service'
        filters += '&&service.name=="{}"'.format(servicename)

    body = {
        'filter': filters,
        "type": object_type,
        "author": username,
        "comment": comment_text}

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json; charset=utf-8'}

    SESSION.post(
        CONFIG['icinga_addr'] + "/v1/actions/add-comment",
        auth=(username, password),
        verify=False,
        headers=headers,
        json=body)

    return

def delete_comments_icinga(username, password, comments):
    '''Delete icinga comments associated with the current user and service/host'''

    headers = {'Accept': 'application/json'}
    for comment in comments:
        if comment['attrs']['author'] == username:
            url = "/v1/actions/remove-comment?comment={}".format(comment['attrs']['__name'])

            res = SESSION.post(
                CONFIG['icinga_addr'] + url,
                auth=(username, password),
                verify=False,
                headers=headers)

            syslog.syslog(json.dumps(res.text))

    return

authenticate_rt(CONFIG['rt_user'], CONFIG['rt_pass'])

COMMENTS = get_comments_icinga(
    CONFIG['icinga_user'],
    CONFIG['icinga_pass'],
    ARGS.host,
    ARGS.service)

if not COMMENTS:
    TICKET_ID = None
else:
    # extract id from comment
    TICKET_ID = TICKETID_REGEX.search(COMMENTS[0]['attrs']['text']).group(2)

if ARGS.type != "ACKNOWLEDGEMENT":
    if ARGS.state == "CRITICAL" or ARGS.state == "DOWN":
        print("Service/host went down")
        if TICKET_ID is None:
            print("Create RT ticket and comment ID")

            RT_ID = create_ticket_rt(
                "{} {} went {}".format(ARGS.host, ARGS.service, ARGS.state))
            add_comment_icinga(
                CONFIG['icinga_user'],
                CONFIG['icinga_pass'],
                ARGS.host,
                ARGS.service,
                '[{} #{}] - ticket created in RT'.format(CONFIG['rt_name'], str(RT_ID)))
        else:
            print("Get comment and comment on RT")
            add_comment_rt(TICKET_ID)
    elif ARGS.state == "OK" or ARGS.state == "UP":
        print("Server/host back up")
        add_comment_rt(TICKET_ID)
        set_status_rt(TICKET_ID)
        delete_comments_icinga(
            CONFIG['icinga_user'],
            CONFIG['icinga_pass'],
            COMMENTS)
else:
    print("Someone acknowledged the problem")
    add_comment_rt(TICKET_ID,)

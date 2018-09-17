#!/usr/bin/env python

'''
This script is to monitor if head_block_time of a given EOS blockchain is up to date. In the case of
head_block_time is X seconds older than current utc timestamp, this script would trigger an email 
alert assuming something bad is happening, either the local blockchain is not full synced with global 
blockchain, or the global blockchain is halted for whatever reason.

'''
import argparse
import json
import os
import requests
import sys
from datetime import datetime

MAX_ALLOWED_DELAY_SECONDS = 60


def alert_head_block_freshness(http_endpoint, alert_email, alert_slack, disable_lock):
    """
    Keyword arguments:
    http_endpoint -- http endpoint of a blockchain node (full node or producer node)
    alert_email -- email address to send an alert in case of stale chain
    """

    print "\n**********************************"
    print "current time = ", datetime.utcnow()
    print "https_endpoint =", http_endpoint
    print "alert_email =", alert_email

    r = None

    try:
        r = requests.get(http_endpoint)
    except:
        print('An error occured when connect to http/s endpoint.')

    if disable_lock is True:
        lock = False
    else:
        lock = os.path.isfile('notified.lock')

    # send alert if the http call is not successful
    if r is None or r.status_code != 200:

        if lock is True:
            print "\nRPC call to http/s endpoint failed, but notification lock is active, not sending alert..."

        else:
            print "\nRPC call to http/s endpoint failed, sending alert..."

            if alert_email is not None:
                os.system(
                    'echo "Failed RPC call to http/s endpoint = {http_endpoint}" | mail -s "Alert: HTTP/S endpoint call is failing!" {email}'
                    .format(http_endpoint=http_endpoint, email=alert_email)
                )

            if alert_slack is not None:
                os.system('echo "Failed RPC call to http/s endpoint = {http_endpoint}" | {slack}'
                          .format(http_endpoint=http_endpoint, slack=alert_slack))

            if disable_lock is False:
                open('notified.lock', 'a').close()

        sys.exit(1)

    obj = json.loads(r.content)
    print "response content =", json.dumps(obj)

    head_block_time_obj = datetime.strptime(obj['head_block_time'][0:19], '%Y-%m-%dT%H:%M:%S')
    print "\nhead_block_time =", head_block_time_obj.strftime('%Y-%m-%dT%H:%M:%S')
    current_utc_time_obj = datetime.utcnow()
    print "current_utc_time =", current_utc_time_obj.strftime('%Y-%m-%dT%H:%M:%S')

    time_diff = current_utc_time_obj - head_block_time_obj
    time_diff_in_seconds = time_diff.total_seconds()

    # send alert if the time delta is no less than 60 seconds
    if time_diff_in_seconds >= MAX_ALLOWED_DELAY_SECONDS:

        if lock is True:
            print "\nhead_block_lagged_by", time_diff_in_seconds, "seconds, but notification lock is active, not sending alert..."

        else:
            if alert_email is not None:
                os.system(
                    'echo "Out of sync BP node behind endpoint = {endpoint}" | mail -s "Alert: EOS blockchain is outdated!" {email}'
                    .format(endpoint=http_endpoint, email=alert_email))

            if alert_slack is not None:
                os.system(
                    'echo "Out of sync BP node behind endpoint = {endpoint}" | {slack}'
                    .format(endpoint=http_endpoint, slack=alert_slack))

            if disable_lock is False:
                open('notified.lock', 'a').close()

        sys.exit(1)

    # nodeos is available and synced, remove the notification lock again
    if os.path.isfile('notified.lock') and disable_lock is False:
        os.remove('notified.lock')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check data freshness of a given blockchain based on http/s call')
    parser.add_argument('-he', '--http_endpoint', help='http endpoint to check against',
                        default='http://127.0.0.1:80/v1/chain/get_info')
    parser.add_argument('-dl', '--disable_lock', help='disable the notification lock, alerts will always be sent',
                        action='store_true')

    requiredArg = parser.add_argument_group('required arguments (at least one of --alert_email and --alert_slack is required)')
    requiredArg.add_argument('-ae', '--alert_email', help='email address to send alert to')
    requiredArg.add_argument('-as', '--alert_slack', help='path to slacktee executable')

    args = parser.parse_args()
    options = vars(args)

    if options.get('alert_email') is None and options.get('alert_slack') is None:
        parser.error('At least one of --alert_email and --alert_slack is required')

    alert_head_block_freshness(options.get('http_endpoint'), options.get('alert_email'),
                               options.get('alert_slack'), options.get('disable_lock'))

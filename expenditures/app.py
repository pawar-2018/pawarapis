# -*- coding: utf-8 -*-

from candidates import candidates
from firebase_admin import credentials, db as firebasedb
from flask import Flask, jsonify
from flask_cors import CORS, cross_origin

import boto3
import collections
import datetime as dt
import firebase_admin
import json
import logging
import os
import random
import requests
import sitelib.utils as utils
import time


# if ENV isn't set, default to 'dev'
env = os.environ.get('ENV', 'dev')

# configure cache & prepare Firebase cert
if env == 'local':
    dynamodb = boto3.resource('dynamodb', endpoint_url='http://dynamodb-local:8000')
    cache = dynamodb.Table('cache-local')

    # read Firebase cert from file
    cert_file = open('firebaseServiceAccountKey.json', 'r')
    cert_json = cert_file.read()

    cred = firebase_admin.credentials.Certificate(json.loads(cert_json))
else:
    dynamodb = boto3.resource('dynamodb')
    cache = dynamodb.Table('cache-{}'.format(env))

    # read Firebase cert from ENV
    cred = firebase_admin.credentials.Certificate(json.loads(os.environ['cert']));

# assume there will never be more than 1,000,000 expenditures (but you never know, amirite?)
apiLimit = 1000000
dateFormat = '%Y-%m-%dT%H:%M:%S'

firebase_app = firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://illinois-calc.firebaseio.com/'
})


app = Flask(__name__)


def retrieve_random_fact(of_the_day):
    rand_fact = None
    used_facts = []

    if of_the_day:
        fact_response = cache.get_item(
            Key = {
                'id': 'fact-of-the-day'
            }
        )

        if 'Item' in fact_response:
            item = fact_response['Item']
            fact_json = item['json']
            rand_fact = json.loads(fact_json)

        used_fact_response = cache.get_item(
            Key = {
                'id': 'used-facts'
            }
        )

        if 'Item' in used_fact_response:
            item = used_fact_response['Item']
            used_facts_json = item['json']
            used_facts = json.loads(used_facts_json)

    if not rand_fact:
        facts_ref = firebasedb.reference('facts')
        #weirdly, leaving out the start_at makes it return a list
        #instead of a dict so we can't see the keys
        allfacts = facts_ref.order_by_key().start_at('0').get()
        all_fact_ids = []

        for key, value in allfacts.items():
            all_fact_ids.append(key)

        # if we don't have any facts left, then reset the used list
        if len(used_facts) >= len(all_fact_ids):
            used_facts = []

        for used_fact_key in used_facts:
            all_fact_ids.remove(used_fact_key)

        rand_fact_id = random.choice(all_fact_ids)
        used_facts.append(rand_fact_id)

        rand_fact = allfacts[rand_fact_id]

        if of_the_day:
            cache.put_item(
                Item = {
                    'id': 'fact-of-the-day',
                    'json': json.dumps(rand_fact),
                    'ttl': int(time.time()) + 86400
                }
            )

            # used facts has no expiry date/time
            cache.put_item(
                Item = {
                    'id': 'used-facts',
                    'json': json.dumps(used_facts)
                }
            )

    return rand_fact


def generate_response(rand_fact):
    cand_expenditures = get_cand_expenditures('rauner')

    # get it before rounding
    spentPerDay = utils.calculateSpentPerDay(float(cand_expenditures['spendingDays']),
                                       float(cand_expenditures['total']))
    spentPerSecond = utils.calculateSpentPerSecond(spentPerDay)
    secondsPerFactUnit = float(rand_fact['amount']) / spentPerSecond

    mins, secs = divmod(secondsPerFactUnit, 60)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)

    text = "#RaunerSpends the %s in " % rand_fact['item']
    prevNum = False
    timecomponents = []
    
    if days:
        timecomponents.append("%d %s" % (days, utils.plural("day", days)))
    
    if hours:
        timecomponents.append("%d%s" % (hours, utils.plural("hr", hours)))
    
    if mins:
        timecomponents.append("%d%s" % (mins, utils.plural("min", mins)))

    text += ", ".join(timecomponents)

    text += " [%s]" % rand_fact['source']

    resp = {'text': text}

    return resp


def get_cand_expenditures(candidate_nick):
    # find a matching committee_id
    committeeId = None

    # default to error message
    response_json = { 'error': 'Candidate not found' }

    for c in candidates:
        if c.get('id') == candidate_nick:
            committeeId = c.get('committeeId')
            break

    if committeeId:
        # try to pull data from cache
        response = cache.get_item(
            Key = {
                'id': candidate_nick
            }
        )

        # if data found in cache, use it
        if 'Item' in response:
            item = response['Item']
            candidate_json = item['json']
            response_json = json.loads(candidate_json)
        # if data not found in cache:
        else:
            # make API call
            response = requests.get('https://www.illinoissunshine.org/api/expenditures/?limit={}&committee_id={}'.format(apiLimit, committeeId))

            apiData = json.loads(json.dumps(response.json()))

            total = 0.0

            for expenditure in apiData['objects'][0]['expenditures']:
                total = total + float(expenditure['amount'])

            firstExpenditure = apiData['objects'][0]['expenditures'][-1]['expended_date']
            spendingDays = utils.calculateSpendingDays(dateFormat, firstExpenditure)
            spentPerDay = utils.calculateSpentPerDay(spendingDays, total)

            response_json = {
                'total': "{0:.2f}".format(total),
                'expendituresCount': len(apiData['objects'][0]['expenditures']),
                'firstExpenditure': firstExpenditure,
                'spendingDays': spendingDays,
                'spentPerDay': "{0:.2f}".format(spentPerDay),
                'spentPerSecond': "{0:.2f}".format(utils.calculateSpentPerSecond(spentPerDay)),
                'timestamp': dt.datetime.strftime(dt.datetime.now(), dateFormat)
            }

            # illinoissunshine data should be cached for one hour
            cache.put_item(
                Item = {
                    'id': candidate_nick,
                    'json': json.dumps(response_json),
                    'ttl': int(time.time()) + 3600
                }
            )
            
    return response_json


# convenience route for development/testing
@app.route('/clear', methods=['GET'])
def clear():
    for c in candidates:
        storage.delete(c.get('id'))

    return 'cache cleared'


@app.route('/facts/random/oftheday', methods=['GET'])
@cross_origin()
def get_random_fact_oftheday():
    rand_fact = retrieve_random_fact(True)
    resp = generate_response(rand_fact)
    return jsonify(resp)


@app.route('/facts/random', methods=['GET'])
@cross_origin()
def get_random_fact():
    # pick a random fact from the db
    # pick a random candidate and get their numbers
    # calculate stuff and return the text
    rand_fact = retrieve_random_fact(False)
    resp = generate_response(rand_fact)
    return jsonify(resp)


@app.route('/candidate/<string:candidate_nick>', methods=['GET'])
@cross_origin()
def get_candidate(candidate_nick):
    # return JSON data about requested candidate *or* error message
    return jsonify(get_cand_expenditures(candidate_nick))


if __name__ == "__main__":
    # TODO: set debug=False for ENV=prod?
    app.run(host="0.0.0.0", debug=True)

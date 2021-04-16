import requests
from obspy import UTCDateTime
import os
import pandas as pd


def req_sta(fout, **params):
    """
    syntax reference: http://service.iris.edu/fdsnws/station/1/
    change url to your preferred data center, reference: https://www.fdsn.org/datacenters/
    """
    # url = "http://service.iris.edu/fdsnws/station/1/query?"
    url = "http://webservices.ingv.it/fdsnws/station/1/query?"
    if 'format' not in params:
        params['format'] = 'text'
    text = _req_url(url, params=params)
    with open(fout, 'w') as f:
        f.write(text)
        print("Success: writing to %s" % fout)


def req_sta_df(**params):
    req_sta('./fdsn_sta.tmp', **params)
    fdsn_sta = pd.read_table('./fdsn_sta.tmp', sep='|', skiprows=1, usecols=[0, 1, 2, 3, 4, 6, 7], names=['net', 'sta', 'stla', 'stlo', 'elev', 'starttime', 'endtime'])
    os.remove('./fdsn_sta.tmp')
    print(fdsn_sta.head())
    return fdsn_sta


def _req_url(url, verbose=True, params={}):
    r = requests.get(url, params=params)
    if verbose:
        print("Connecting to:")
        print(r.url)
    if r.status_code == 404:
        raise ValueError("404: Bad request or no data")
    elif r.status_code == 204:
        print("no data")
        return ""
    r.raise_for_status()
    return r.text


def req_evt_df(**params):
    req_event('./fdsn_evt.tmp', **params)
    fdsn_evt = pd.read_table('fdsn_evt.tmp', sep='|',  comment='#', 
              usecols=[0, 1, 2, 3, 4, 10], 
              names=['evid', 'time', 'evla', 'evlo', 'evdp', 'mag'])
    os.remove('./fdsn_evt.tmp')
    print(fdsn_evt.head())
    print(fdsn_evt.tail())
    return fdsn_evt


def req_event(fpath, **params):
    """
    reference: http://service.iris.edu/fdsnws/event/1/
    change url to your preferred data center, reference: https://www.fdsn.org/datacenters/
    """
    url = "http://webservices.ingv.it/fdsnws/event/1/query?"
    if 'format' not in params:
        params['format'] = 'text'
    if 'starttime' in params and 'endtime' in params:
        step = 24 * 3600 * 365
        print("Request data year by year, to avoid exceding the limit")
        start0 = UTCDateTime(params['starttime'])
        end0 = UTCDateTime(params['endtime'])
        cur = start0
        text = ""
        while cur + step < end0:
            params['starttime'] = str(cur)[:-1]
            params['endtime'] = str(cur+step)[:-1]
            cur = cur + step
            text += _req_url(url, params=params)

        params['starttime'] = str(cur)[:-1]
        params['endtime'] = str(end0)[:-1]
        text += _req_url(url, params=params)
    else:
        text = _req_url(url, params=params)

    with open(fpath, 'w') as f:
        f.write(text)
        print("Success: writing to %s" % fpath)


if __name__ == '__main__':
    evt = req_evt_df(starttime='2010-09-01', endtime='2013-09-01', minmag=7, format='text')
    sta = req_sta_df(minlat=42, maxlat=44, minlon=12, maxlon=14, format='text')
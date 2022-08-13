import obspy
import requests
from obspy import UTCDateTime
import os
import pandas as pd
from io import BytesIO
from scipy import signal
import numpy as np
import warnings
import sys
import time


def req_sta(fout, baseurl, **params):
    """
    syntax reference: http://service.iris.edu/fdsnws/station/1/
    change url to your preferred data center, reference: https://www.fdsn.org/datacenters/
    """
    # url = "http://service.iris.edu/fdsnws/station/1/query?"
    # url = "http://webservices.ingv.it/fdsnws/station/1/query?"
    # baseurl = "http://service.iris.edu/ph5ws/station/1/query?"
    if 'format' not in params:
        params['format'] = 'text'
    text = _req_url(baseurl, params=params)
    with open(fout, 'w') as f:
        f.write(text)
        print("Success: writing to %s" % fout)


def req_sta_df(baseurl, **params):
    req_sta('./fdsn_sta.tmp', baseurl, **params)
    fdsn_sta = pd.read_table('./fdsn_sta.tmp', sep='|', skiprows=1, usecols=[0, 1, 2, 3, 4, 6, 7], names=['net', 'sta', 'stla', 'stlo', 'elev', 'starttime', 'endtime'])
    os.remove('./fdsn_sta.tmp')
    print(fdsn_sta.head())
    return fdsn_sta


def _req_url(url, verbose=True, out_format='text', params={}):
    time.sleep(0.01)
    r = requests.get(url, params=params)
    if verbose:
        print("Connecting to:")
        print(r.url)
    if r.status_code == 404:
        raise ValueError("404: Bad request or no data")
    elif r.status_code == 204:
        print("no data: %s" % r.url)
        return ""
    r.raise_for_status()
    if out_format == 'text':
        return r.text
    elif out_format == 'byte':
        return r.content


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


def req_conti(service, fpath, **params):
    """
    reference: http://service.iris.edu/ph5ws/dataselect/1/
    """
    if service == "PH5WS":
        url = "http://service.iris.edu/ph5ws/dataselect/1/query?reqtype=fdsn"
    elif service == "FDSNWS":
        url = "http://service.iris.edu/fdsnws/dataselect/1/query?"
    params['nodata'] = '204'
    ds_factor = params.pop('_ds_factor', False)
    path_resp_xml = params.pop('_path_resp_xml', False)
    content = _req_url(url, verbose=False, out_format='byte', params=params)
    if not content:
        return 0
    st = obspy.read(BytesIO(content))
    del content
    st = pre_process_conti(st, ds_factor, path_resp_xml)
    if len(st) == 0:
        return 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        st.write(fpath, format=params['format'])
    return st[0].stats.npts

def pre_process_conti(st, ds_factor, path_resp_xml):
    pre_filt = [0.02, 0.025, 2, 2.5]
    try:
        for ii in range(len(st)):
            st[ii].data = np.float64(st[ii].data)
            st[ii].data = signal.detrend(st[ii].data,type='constant')
            st[ii].data = signal.detrend(st[ii].data,type='linear')
    except ValueError as e:
        print(st, file=sys.stderr)
        print(e, file=sys.stderr)
        return obspy.Stream()
    if len(st) > 1:
        try:
            st.merge(method=1, fill_value=np.nan)
        except Exception as e:
            print(st, file=sys.stderr)
            print(e, file=sys.stderr)
            return obspy.Stream()
    if np.sum(np.isnan(st[0].data)) / len(st[0].data) > 0.05:
        print("Too many gap:%s" % str(st))
        return obspy.Stream()
    st[0].data = np.nan_to_num(st[0].data, nan=0.0)
    if ds_factor:
        for dsf in ds_factor:
            st.decimate(dsf)
    if path_resp_xml:
        try:
            inv = obspy.read_inventory(path_resp_xml)
            st.remove_response(inventory=inv, output='VEL', pre_filt=pre_filt)
        except ValueError as e:
            print("Can't remove response %s" % str(st), file=sys.stderr)
            return obspy.Stream()
    return st

if __name__ == '__main__':
    pass
    # evt = req_evt_df(starttime='2010-09-01', endtime='2013-09-01', minmag=7, format='text')
    # sta = req_sta_df(baseurl = "http://webservices.ingv.it/fdsnws/station/1/query?", minlat=42, maxlat=44, minlon=12, maxlon=14, format='text')
import obspy
import numpy as np
import matplotlib.pyplot as plt
import subprocess


def rm_instr_resp(st, respfile, resp_type, pre_filt, ytype):
    """
    remove instrument response from seismic data
    :param st: seismic data, obspy.stream
    :param respfile: response file
    :param resp_type: type of response file, now support 'pz'
    :param pre_filt: pre filter [f1, f2, f3, f4]
    :param ytype: type of y value. 'none':displacement, 'vel':velocity
    :return:
    """
    if resp_type == 'pz':
        pz = read_pole_zero(respfile)
        st.simulate(paz_remove=pz, pre_filt=pre_filt)
        if ytype == 'none':
            pass
        elif ytype == 'vel':
            st[0].data = np.diff(st[0].data) / st[0].stats.delta
        else:
            raise ValueError('unknown ytype %s' % ytype)
    else:
        raise ValueError('unknown response type %s' % resp_type)


def read_pole_zero(pzfile):
    """
    read pole zero file
    :param pzfile: pz filename
    :return: dict, 'zeros', 'poles', 'constant'
    """
    pz = {}
    f = open(pzfile, 'r')
    line = f.readline()
    while line[0] == '*':
        line = f.readline()
    # read zeros
    num_zeros = int(line.split()[1])
    zeros = []
    for _ in range(num_zeros):
        line = f.readline()
        temp = list(map(float, line.split()))
        zeros.append(complex(temp[0], temp[1]))
    pz['zeros'] = zeros
    # read poles
    line = f.readline()
    num_poles = int(line.split()[1])
    poles = []
    for _ in range(num_poles):
        line = f.readline()
        temp = list(map(float, line.split()))
        poles.append(complex(temp[0], temp[1]))
    pz['poles'] = poles
    # read constant
    constant = float(f.readline().split()[1])
    pz['sensitivity'] = constant
    pz['gain'] = 1.0
    f.close()
    return pz


def func_pz(pz):
    """
    get response function H(f) from pz info
    :param pz: output of read_pole_zero
    :return: function H(f)
    """
    def H(f):
        s = f * complex(0, 1) * 2 * np.pi
        result = pz['sensitivity']
        for z in pz['zeros']:
            result *= (s - z)
        for p in pz['poles']:
            result /= (s - p)
        return result
    return H


def plot_resp(resp_func, freqs):
    """
    plot response from response function
    :param resp_func: H(f)
    :param freqs: frequency points
    :return: None
    """
    resp = resp_func(freqs)
    amps = np.abs(resp)
    phas = np.angle(resp, deg=True)
    fig, ax = plt.subplots(nrows=2, sharex=True)
    ax[0].plot(freqs, amps)
    ax[0].set_title("Magnitude Response")
    ax[1].plot(freqs, phas)
    ax[1].set_title("Phase Response")
    ax[1].set_xlabel("Frequency (Hz)")
    ax[0].grid()
    ax[1].grid()
    plt.show()


def benchmark_pz(sac, pz, pre_filt, xtype='none'):
    """
    使用solo数据时，对比结果主要取决于pre_filt参数，当设置为0.1-8时，吻合很好，
    平均误差小于0.1%，当带通滤波器f2设为更小值时，误差会更大，猜测是因为二者实现的滤波器不同导致的，
    去除仪器响应本身是基本可靠的。
    """
    st0 = obspy.read(sac)
    st0.detrend("demean")
    st0.detrend("linear")
    st0.taper(max_percentage=0.05)
    rm_instr_resp(st0, pz, 'pz', pre_filt, xtype)
    st0[0].write('temp0.sac', format='SAC')
    p = subprocess.Popen(['sac'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    s = ""
    s += "r %s\n" % sac
    s += "rmean;rtrend\n"
    s += "taper\n"
    s += "transfer from polezero s %s freq %f %f %f %f\n" % ((pz, ) + tuple(pre_filt))
    if xtype == 'vel':
        s += 'dif\n'
    s += "w temp1.sac\n"
    s += "q\n"
    print(s)
    p.communicate(s.encode())
    st1 = obspy.read('temp1.sac')
    d0 = st0[0].data
    d1 = st1[0].data
    print('max value\npython %f, sac %f' % (np.max(d0), np.max(d1)))
    d0 = d0 / np.max(d0)
    d1 = d1 / np.max(d1)
    dmean = np.mean(abs(d0 - d1))
    dmax = np.max(abs(d0 - d1))
    print("mean diff %f\nmax diff %f" % (dmean, dmax))
    # subprocess.run('rm temp1.sac temp0.sac', shell=True)


if __name__ == '__main__':
    H = func_pz(read_pole_zero('./respfile'))
    plot_resp(H, np.arange(0, 100, 0.1))
import subprocess
import numpy as np
import os


def gmt_wrap(ins, *bins):
    insl = ins.split()
    out = subprocess.run(insl + list(bins), capture_output=True)
    if out.stderr:
        print(out.stderr.decode())
    return out.stdout.decode()


def cm2inch(*tupl):
    inch = 2.54
    if isinstance(tupl[0], tuple):
        return tuple(i/inch for i in tupl[0])
    else:
        return tuple(i/inch for i in tupl)


def txt2bi(filei, fileo, use_cols=False, skiprows=1):
    """
    convert text table file to binary numpy file
    only do the conversion if input file is newer than the binary file
    """
    if os.path.exists(fileo) and os.path.getctime(fileo) > os.path.getctime(filei):
        print("%s is already newest" % fileo)
    else:
        print("Updating: %s" % fileo)
        temp = np.loadtxt(filei, skiprows=skiprows)
        if use_cols:
            temp = temp[:, use_cols]
        np.save(fileo, temp)
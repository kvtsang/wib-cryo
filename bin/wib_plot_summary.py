#!/usr/bin/env python3

import os
import sys
import argparse
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import itertools
from glob import glob


import seaborn as sns

def main():
    sns.set_context('talk')
    sns.set_style('ticks')

    parser = argparse.ArgumentParser(description='WIB Cryo Summary Plot')
    parser.add_argument('indir', metavar='DIRECTORY', help='input directory')

    args = parser.parse_args()
    files = glob(os.path.join(args.indir, 'stats_*.csv'))

    prefixes = set()
    suffixes = set()
    for fpath in files:
        fname = os.path.basename(fpath)
        prefix = fname.split('_ASIC')[0].replace('stats_', '')
        prefixes.add(prefix)

        i = fname.find('_ASIC')
        suffix = fname[i+7:].replace('.csv', '')
        suffixes.add(suffix)


    for prefix, suffix in itertools.product(prefixes, suffixes):
        fig, axes = plt.subplots(2, 2, figsize=(8,6), sharex=True, sharey='row')
        for asic in [0,1]:
            fpath = os.path.join(args.indir, f'stats_{prefix}_ASIC{asic}_{suffix}.csv')

            stats =  pd.read_csv(fpath)

            axes[0, asic].plot(stats['mean'])
            axes[1, asic].plot(stats['std'])

            axes[0, asic].set_title(f'ASIC{asic}')
            axes[1, asic].set_xlabel('Ch.')

        axes[0,0].set_ylabel('Mean [ADC]')
        axes[1,0].set_ylabel('Std. [ADC]')

        outpath = os.path.join(args.indir, f'summary_{prefix}_{suffix}.png')
        fig.suptitle(prefix)
        fig.tight_layout(rect=(0,0,1,0.97))
        fig.savefig(outpath)


if __name__ == '__main__':
    main()

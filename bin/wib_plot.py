#!/usr/bin/env python3

import os
import sys
import argparse
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal
from glob import glob

import seaborn as sns

def mean_psd(adcs, fs, sub_ped=True, return_dB=True, algo=signal.periodogram, **kwargs):
    """
    Mean PSD for multiple waveforms captured in the same conditions

    Arguments
    ---------
    adcs: (N, ) array_like
        List of N waveforms
    fs: float
        Sampling frequency
    sub_ped: bool, optional
        Pedestal subtraction. Defaults to rue
    return_dB: bool, optional
        Return in units of dB. Defaults to rue
    algo: function, optional
        Algorithm to estimate power spectrum. Defaults to cipy.signal.welch    kwargs: dict or keyword arguments, optional
        Arguments to lgo
    Returns
    -------
    freq: (M, ) ndarray
        Frequency of PSD
    pxx: (M, ) ndarray
        Mean power specturm
    """

    wfms = adcs - adcs.mean(axis=1, keepdims=True) if sub_ped else adcs
    pxx = np.mean([algo(x, fs=fs, **kwargs)[1] for x in wfms], axis=0)
    freq = np.linspace(0, fs/2., len(pxx))

    if sub_ped:
        pxx = pxx[1:]
        freq = freq[1:]

    if return_dB:
        pxx = 10 * np.log10(pxx)

    return freq, pxx

def heatmap(data, row_labels, col_labels, ax=None,
	cbar_kw={}, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (N, M).
    row_labels
        A list or array of length N with the labels for the rows.
    col_labels
        A list or array of length M with the labels for the columns.
    ax
        A atplotlib.axes.Axesinstance to which the heatmap is plotted.  If
        not provided, use current axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to atplotlib.Figure.colorbar  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to mshow
    """

    if not ax:
        ax = plt.gca()

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    #cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    #cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[1]))
    ax.set_yticks(np.arange(data.shape[0]))
    # ... and label them with the respective list entries.
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=True, bottom=False,
                   labeltop=True, labelbottom=False)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation='vertical',
             ha="left", va='center',
             rotation_mode="anchor")

    # Turn spines off and create white grid.
    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    #return im, cbar
    return im

def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
		 textcolors=("black", "white"),
		 threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        atplotlib.ticker.Formatter  Optional.
    textcolors
        A pair of colors.  The first is used for values below a threshold,
        the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to extused to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a extfor each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts

def plot_psd(adcs, fs=2e6, num=None):
    fig, axes = plt.subplots(8, 8, figsize=(32, 16),
                            sharex=True, sharey=True,
                            num=num, clear=True)

    for ch, ax in zip(range(64), axes.flat):
        data = adcs[:,ch]
        std = np.std(data - data.mean(axis=-1, keepdims=True))
        
        freq, pxx = mean_psd(data, fs=fs)
        ax.plot(freq*1e-6, pxx, linewidth=1, alpha=0.8)
        ax.text(0.99, 0.97, f'ch{ch:02} std:{std:.1f}', ha='right', va='top', 
                transform=ax.transAxes)

    fig.text(0.5, 0, 'Frequency [MHz]', ha='center', va='bottom')
    fig.text(0., 0.5, 'Power Spectrum [dB]', rotation='vertical', ha='left', va='center')
    return fig

def plot_mcorr(adcs, num=None):
    adcs0 = adcs - adcs.mean(axis=-1, keepdims=True)
    mcorr = np.corrcoef(np.swapaxes(adcs0, 0, 1).reshape(64, -1))

    fig, ax = plt.subplots(figsize=(32,32), num=num, clear=True)
    labels = [f'ch{ch:02}' for ch in range(64)]
    im = heatmap(mcorr, labels, labels, ax=ax, cmap='RdBu', vmax=1, vmin=-1)
    texts = annotate_heatmap(im, valfmt='{x:.1f}')

    return fig

def plot_wfm(adcs, num=None):
    
    fig, axes = plt.subplots(8, 8, figsize=(32, 16),
                            sharex=True,
                            num=num, clear=True)

    for ch, ax in zip(range(64), axes.flat):
        ax.plot(adcs[0,ch], linewidth=1, alpha=0.8, color='grey')
        ax.text(0.99, 0.97, f'ch{ch:02}', ha='right', va='top', transform=ax.transAxes)

    fig.text(0.5, 0, 'Sample', ha='center', va='bottom')
    fig.text(0., 0.5, 'ADC', rotation='vertical', ha='left', va='center')
    
    return fig

def plot_pulse(adcs, num=None):
    return plot_wfm(adcs, num)

def save_stats(adcs, output):
    table = {
        'mean' : adcs.mean(axis=(0,2)),
        'std' : adcs.std(axis=-1).mean(axis=0),
    }
    df = pd.DataFrame(table)
    df.to_csv(
        f'{output}.txt', index_label='ch', 
        float_format='%.3f',
    )

def plot_std(adcs, num=None):
    table = adcs.std(axis=-1).mean(axis=0)
    fig, ax = plt.subplots(figsize=(8,6), 
                           num=num, clear=True)
    ax.plot(table)
    ax.set_xlabel('Channel')
    ax.set_ylabel('std [ADC]')
    return fig

def plot(adcs, femb, title, output, plot_func, **kwargs):
    fembs = [femb] if isinstance(femb, int) else femb

    for i in fembs:
        for asic in [0,1]:
            out_prefix = output.format(i, asic)
            print(out_prefix)
            data = adcs[:,i,:64] if asic == 0 else adcs[:,i,64:]
            fig = plot_func(data, **kwargs)
            fig.suptitle(title.format(i, asic))
            fig.tight_layout(rect=(0,0,1,0.97))
            fig.savefig(f'{out_prefix}.png')

            if plot_func.__name__ == 'plot_std':
                save_stats(data, out_prefix.replace('std_', 'stats_'))

def _bind(parser, func, **kwargs):
    name = func.__name__
    alias = name.replace('plot_', '')
    p = parser.add_parser(func.__name__, aliases=[alias], **kwargs)
    p.add_argument('-i', '--input', required=True)
    p.add_argument('-d', '--dataset', required=True)
    p.add_argument('--femb', type=int, choices=range(4), nargs='+')
    p.add_argument('--cold', action='store_true')
    
    if func.__name__ == 'plot_psd':
        p.add_argument('--fs', type=float, default=1e6/0.512)

    p.set_defaults(func=func)

def _read(path):
    if os.path.isfile(path):
        print(f'Reading {path}')
        content = np.load(path)
        return np.array([content['data']])

    if os.path.isdir(path):
        files = glob(os.path.join(path, '*.npz'))

        print(f'Reading {len(files)} files from {path}')
        data = [np.load(path)['data'] for path in files]

        # slightly different sizes returned by spy buffer
        sizes = [arr.shape[-1] for arr in data]
        n = np.min(sizes)
        data = np.array([arr[:,:,:n] for arr in data])
        return data

    print(f"No input file in {path}", file=sys.stderr)
    sys.exit(1)

def _parse_tp(path):
    i = path.find('0x39')
    if i == -1: return None

    status = int(path[i:i+5], 0)
    _map = {
        0x391 : '0u6s',
        0x395 : '1u2s',
        0x399 : '2u4s',
        0x39d : '3u6s',
        0x390 : '0u6s',
        0x394 : '1u2s',
        0x398 : '2u4s',
        0x39c : '3u6s',
    }
    return _map.get(status)


def main():
    sns.set_context('talk')
    sns.set_style('white')

    parser = argparse.ArgumentParser(description='WIB Cryo Plot')
    subparsers = parser.add_subparsers()
    _bind(subparsers, plot_psd)
    _bind(subparsers, plot_mcorr)
    _bind(subparsers, plot_wfm)
    _bind(subparsers, plot_pulse)
    _bind(subparsers, plot_std)

    args = parser.parse_args()
    kwargs = vars(args).copy()
    kwargs.pop('input')
    kwargs.pop('dataset')
    kwargs.pop('femb')
    kwargs.pop('cold')
    kwargs.pop('func')

    plot_type = args.func.__name__.replace('plot_', '')
    tp = _parse_tp(args.input)
    cond = 'Cold' if args.cold else 'Room'
    title = f'{args.dataset}_FEMB{{}}_ASIC{{}}_{tp}_{cond}'
    output = f'{plot_type}_{args.dataset}_FEMB{{}}_ASIC{{}}_{tp}_{cond}'

    data = _read(args.input)

    if args.femb is None:
        is_active = np.any(data, axis=(0,2,3))
        args.femb = np.where(is_active)[0]

    plot(data, args.femb, title, output, args.func, **kwargs)

if __name__ == '__main__':
    main()

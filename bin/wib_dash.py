#!/usr/bin/env python3
#from jupyter_dash import JupyterDash

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template


from flask_caching import Cache

import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
from scipy.signal import periodogram
import argparse

class FakeWIB:
    @staticmethod
    def _generator(n):
        data = np.random.normal(2048, 5, size=(4,128,n)).astype(int)
        data[data<0] = 0
        data[data>4095] = 4095
        return data

    def __init__(self, generator=None):
        if generator is None:
            generator = FakeWIB._generator
        self._generate = generator
        
    def acquire_data(self):
        n = 2162
        t = np.zeros((2,n))
        adcs = self._generator(n)
        time.sleep(3)
        return t, adcs

def _draw_pixel(data, femb):
    adcs = data[femb]
    fig = px.imshow(adcs,
                    labels=dict(x='Sample', y='Channel'),
                    aspect='square',
                    color_continuous_scale='gray_r')
    fig.update_layout(
        height=320,
        width=320,
        title=f'FEMB{femb}',
        xaxis_title='Sample',
        yaxis_title='Channel',
    )
    return fig

def _draw_mean_std(data, femb):
    adcs = data[femb]
    avg = adcs.mean(axis=-1)
    std = adcs.std(axis=-1)
    
    #fig = go.Figure(layout=dict(height=480, width=480))
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        y=std,
        yaxis='y',
        mode='markers+lines'
    ))
    
    fig.add_trace(go.Scatter(
        y=avg,
        yaxis='y2',
        mode='markers+lines'
    ))
    
    fig.update_layout(
        height=320,
        title=f'FEMB{femb} ADC Mean and Std.',
        xaxis_title='Channel',
        yaxis=dict(title='std [ADC]', domain=[0,0.49], zeroline=False),
        yaxis2=dict(title='mean [ADC]', domain=[0.51,1], zeroline=False),
        showlegend=False,
    )
    return fig

def _draw_hist_adcs(data, femb, ch):
    adcs = data[femb, ch]

    fig = go.Figure(
        go.Histogram(
            x=adcs,
            xbins=dict(size=1),
        ),
    )
    #fig.update_layout(width=360, height=360)
    fig.update_layout(
        height=320,
        width=320,
        title=f'FEMB{femb} Ch{ch:02} ADC',
        xaxis_title='ADC',
        yaxis_title='Counts',
        showlegend=False)
    return fig

def _draw_hist_ts(ts, femb):
    t = ts[femb//2]
    dt = np.diff(t)

    fig = go.Figure(
        go.Histogram(
            x=dt,
            xbins=dict(size=1),
        ),
    )
    #fig.update_layout(width=360, height=360)
    fig.update_layout(
        height=320,
        width=320,
        title=f'Buffer {femb//2}',
        xaxis_title='Delta Timestamp',
        yaxis_title='Counts',
        showlegend=False)
    fig.update_yaxes(type="log")
    return fig

def _draw_hist_delta_adcs(data, femb, ch):
    adcs = data[femb, ch]
    diff = np.fmod(np.diff(adcs.astype(int)), 4096)

    fig = go.Figure(
        go.Histogram(
            x=diff,
            xbins=dict(size=1),
        ),
    )
    #fig.update_layout(width=360, height=360)
    fig.update_layout(
        height=320,
        width=320,
        title=f'FEMB{femb} Ch{ch:02} Delta ADC',
        xaxis_title='Delta ADC',
        yaxis_title='Counts',
        showlegend=False)
    return fig
  
def _draw_wfm(data, femb, ch):
    wfm = data[femb, ch]
    fig = px.line(wfm)
    fig.update_layout(
        height=320,
        title=f'FEMB{femb} Ch{ch:02}',
        xaxis_title='Sample',
        yaxis_title='ADC',
        showlegend=False
    )

    hist = _draw_hist_adcs(data, femb, ch)
    return fig, hist

def _draw_delta_adcs(data, femb, ch):
    adcs = data[femb, ch]
    diff = np.fmod(np.diff(adcs.astype(int)), 4096)

    fig = px.line(diff)
    fig.update_layout(
        height=320,
        title=f'FEMB{femb} Ch{ch:02}',
        xaxis_title='Sample',
        yaxis_title='Delta ADC',
        showlegend=False
    )

    hist = _draw_hist_delta_adcs(data, femb, ch)
    return fig, hist

def _draw_psd(data, femb, ch):
    wfm = data[femb, ch].astype(float).copy()
    wfm -= wfm.mean() #sub. pedestal
    
    freq, pxx = periodogram(wfm, fs=2e6)
    freq *= 1e-3
    pxx_dB = 10 * np.log10(pxx)
    
    fig = px.line(x=freq[1:], y=pxx_dB[1:])
    fig.update_layout(
        height=320,
        title=f'FEMB{femb} Ch{ch:02}',
        xaxis_title='Freqency [kHz]',
        yaxis_title='PSD [dB ADC/Hz]',
        showlegend=False
    )

    hist = _draw_hist_adcs(data, femb, ch)
    return fig, hist

def _draw_timestamp(ts, femb):
    femb = int(femb) 
    buf_idx = femb//2
    
    t = ts[buf_idx] 
    fig = px.line(t & 0xfffff)
    fig.update_layout(
        height=320,
        title=f'Buffer {buf_idx},  t0: {hex(t[0])}',
        xaxis_title='Sample',
        yaxis_title=f'Timestamp & 0xFFFFF',
        showlegend=False
    )
    hist = _draw_hist_ts(ts, femb)
    return fig, hist

def _draw_delta_timestamp(ts, femb):
    femb = int(femb) 
    buf_idx = femb//2
    t = ts[buf_idx]
    
    fig = px.line(np.diff(t))
    fig.update_layout(
        height=320,
        title=f'Buffer {buf_idx},  t0: {hex(t[0])}',
        xaxis_title='Sample',
        yaxis_title=f'Delta Timestamp',
        showlegend=False
    )

    hist = _draw_hist_ts(ts, femb)
    return fig, hist

def _make_options(items):
    options = [{'label':x, 'value':x} for x in items]
    return options

# Build App

load_figure_template("flatly")
#app = JupyterDash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = html.Div([
    html.H1("WIB-CRYO"),
    
    dbc.InputGroup(
        [
            dbc.Select(
                id='wib_type',
                options=[{'label':k, 'value':k} for k in ['WIB', 'FakeWIB']],
                value='WIB',
            ),
            dbc.Input(id='wib_src', type='text'),
        ]
    ),
    
    dbc.InputGroup(
        [
            dbc.Select(
                id='femb',
                options=[{'label': f'FEMB {i}', 'value': i} for i in range(4)],
                value='0',
            ),
            dbc.Select(
                id='channel',
                options=[{'label':f'Ch {i:03}', 'value':i} for i in range(128)],
                value='0',
            ),
            dbc.Select(
                id='buffer',
                options=_make_options(['buf0 + buf1', 'buf0', 'buf1']),
                value='buf0 + buf1',
            ),
            dbc.Input(id='last_update', value=-1, disabled=True),
            dbc.Button('Acquire', id='acquire', color='secondary'),
        ]
    ),

    html.Hr(),
    
    dbc.Row(
        [
            dbc.Col(dcc.Graph(id='pixel'), width=5),
            dbc.Col(dcc.Graph(id='mean_std'), width=7),
        ],
        no_gutters=True,
    ),

    
    html.Hr(),
    
    dbc.RadioItems(id='fig_ch_type', 
                   options=_make_options(['PSD', 'Waveform', 'Delta ADC', 'Timestamp', 'Delta Timestamp']),
                   value='PSD',
                   inline=True,
                  ),

    dbc.Row(
        [
            dbc.Col(dcc.Graph(id='fig_ch'), width=7),
            dbc.Col(dcc.Graph(id='hist_adcs'), width=5),
        ],
        no_gutters=True,
    ),

    
    dcc.Store(id='timestamp')
])


# In[6]:


cache = Cache(
    app.server,
    config={
        'CACHE_TYPE': 'SimpleCache',
        'CACHE_DEFAULT_TIMEOUT': 300
    }
)


# In[7]:


@app.callback(
    Output('timestamp', 'data'),
    Input('acquire', 'n_clicks_timestamp'),
    State('wib_type', 'value'),
    State('wib_src', 'value'),
    State('buffer', 'value'),
    State('timestamp', 'data')
)
def _on_acquire(timestamp, wib_type, wib_src, buf, last_update):
    if timestamp is None:
        raise PreventUpdate
    
    kwargs = {}
    if wib_type == 'WIB':
        from wib import WIB
        wib = WIB(wib_src)
        if buf == 'buf0':
            kwargs['buf1'] = False
        elif buf == 'buf1':
            kwargs['buf0'] = False
    elif wib_type == 'FakeWIB':
        wib = FakeWIB()
    else:
        raise PreventUpdate
        
    cache.clear()
    ts, data = wib.acquire_data(**kwargs)
    cache.set('data', data)
    cache.set('ts', ts)
    return timestamp


# In[8]:


@app.callback(
    Output('last_update', 'value'),
    Input('timestamp', 'data'),
)
def _set_timestamp(timestamp):
    return timestamp

@app.callback(
    Output('pixel', 'figure'),
    Output('mean_std', 'figure'),
    Input('timestamp', 'data'),
    Input('femb', 'value'),
)
def _update_figs_femb(timestamp, femb):
    if timestamp is None:
        raise PreventUpdate
        
    femb = int(femb)
    data = cache.get('data')
    
    output = (
        _draw_pixel(data, femb),
        _draw_mean_std(data, femb),
    )
    
    return output

@app.callback(
    Output('fig_ch', 'figure'),
    Output('hist_adcs', 'figure'),
    Input('timestamp', 'data'),
    Input('femb', 'value'),
    Input('channel', 'value'),
    Input('fig_ch_type', 'value')
)
def _update_fig_ch(timestamp, femb, ch, fig_type):
    if timestamp is None:
        raise PreventUpdate
        
    femb = int(femb)
    ch = int(ch)
    
    if fig_type == 'PSD':
        data = cache.get('data')
        return _draw_psd(data, femb, ch)
    
    if fig_type == 'Waveform':
        data = cache.get('data')
        return _draw_wfm(data, femb, ch)

    if fig_type == 'Delta ADC':
        data = cache.get('data')
        return _draw_delta_adcs(data, femb, ch)

    if fig_type == 'Timestamp':
        ts = cache.get('ts')
        return _draw_timestamp(ts, femb)

    if fig_type == 'Delta Timestamp':
        ts = cache.get('ts')
        return _draw_delta_timestamp(ts, femb)

@app.callback(
    Output('channel', 'value'),
    Input('pixel', 'clickData'),
    Input('mean_std', 'clickData'),
)
def _select_ch(clk_pixel, clk_mean_std):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trig_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trig_id == 'pixel':
        return clk_pixel['points'][0]['y']
    
    if trig_id == 'mean_std':
        return clk_mean_std['points'][0]['x']

    raise PreventUpdate
    
@app.callback(
    Output('wib_src', 'placeholder'),
    Output('wib_src', 'disabled'),
    Output('wib_src', 'value'),
    Input('wib_type', 'value'),
)
def _set_wib_type(wib_type):
    if wib_type == 'WIB':
        return 'Enter WIB IP Address', False, None
    return '', True, None

parser = argparse.ArgumentParser(description='WIB-CRYO dash app')
parser.add_argument('-p', dest='port', default=8050)

if __name__ == '__main__':
    args = parser.parse_args()
    app.run_server(debug=True, port=args.port)
    #app.run_server(mode='jupyterlab')

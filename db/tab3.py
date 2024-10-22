from dash import dcc
from dash import html
import plotly.graph_objs as go

def render_tab(df):

    layout = html.Div([html.H1('Kanały sprzedaży',style={'text-align':'center'}),
                        html.Div([dcc.DatePickerRange(id='heatmap_range',
                        start_date=df['tran_date'].min(),
                        end_date=df['tran_date'].max(),
                        display_format='YYYY-MM-DD')],style={'width':'50%','text-align':'center'}),
                        html.Div([html.Div([dcc.Graph(id='heatmap_store_type')], style={'width':'55%'}),
                        html.Div([dcc.Dropdown(id='store_dropdown',
                                options=[{'label': store_type, 'value': store_type} for store_type in df['Store_type'].unique()],
                                value=df['Store_type'].unique()[0]),
                                dcc.Graph(id='hist_store_type')], style={'width': '45%'})], style={'display': 'flex'}),
                       html.Div(id='temp-out')
                        ])

    return layout
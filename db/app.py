import pandas as pd
import numpy as np
import datetime as dt
import os
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
from dash_auth import BasicAuth
import plotly.graph_objs as go
import tab1
import tab2
import tab3

# Wczytanie danych

class DB:
    def __init__(self):
        self.transactions = DB.transation_init()
        self.cc = pd.read_csv('country_codes.csv',index_col=0)
        self.customers = pd.read_csv('customers.csv',index_col=0)
        self.prod_info = pd.read_csv('prod_cat_info.csv')

    @staticmethod
    def transation_init():
        transactions = pd.DataFrame()
        src = 'transactions'
        for filename in os.listdir(src):
            transactions = pd.concat([transactions, pd.read_csv(os.path.join(src,filename),index_col=0)])

        def convert_dates(x):
            try:
                return dt.datetime.strptime(x,'%d-%m-%Y')
            except:
                return dt.datetime.strptime(x,'%d/%m/%Y')

        transactions['tran_date'] = transactions['tran_date'].apply(lambda x: convert_dates(x))

        return transactions

    def merge(self):
        df = self.transactions.join(self.prod_info.drop_duplicates(subset=['prod_cat_code'])
        .set_index('prod_cat_code')['prod_cat'],on='prod_cat_code',how='left')

        df = df.join(self.prod_info.drop_duplicates(subset=['prod_sub_cat_code'])
        .set_index('prod_sub_cat_code')['prod_subcat'],on='prod_subcat_code',how='left')

        df = df.join(self.customers.join(self.cc,on='country_code')
        .set_index('customer_Id'),on='cust_id')

        df['DOB'] = pd.to_datetime(df['DOB'], format='%d-%m-%Y')

        def count_age(row):
            return (pd.to_datetime(dt.date.today()) - row['DOB']) / np.timedelta64(1, 'Y')

        df['Age'] = df.apply(lambda row: count_age(row), axis=1)

        self.merged = df


df = DB()
df.merge()

# Budowa podstawowego layoutu

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

USERNAME_PASSWORD = [['user','pass']]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

auth = BasicAuth(app,USERNAME_PASSWORD)

app.layout = html.Div([html.Div([dcc.Tabs(id='tabs',value='tab_1',children=[
                            dcc.Tab(label='Sprzedaż globalna',value='tab_1'),
                            dcc.Tab(label='Produkty',value='tab_2'),
                            dcc.Tab(label='Kanały sprzedaży',value='tab_3')
                            ]),
                            html.Div(id='tabs_content')
                    ],style={'width':'80%','margin':'auto'})],
                    style={'height':'100%'})


# Callbacks

@app.callback(Output('tabs_content','children'),[Input('tabs','value')])
def render_content(tab):

    if tab == 'tab_1':
        return tab1.render_tab(df.merged)
    elif tab == 'tab_2':
        return tab2.render_tab(df.merged)
    elif tab == 'tab_3':
        return tab3.render_tab(df.merged)
    
## tab1 callbacks
@app.callback(Output('bar_sales','figure'),
    [Input('sales_range','start_date'),Input('sales_range','end_date')])
def tab1_bar_sales(start_date,end_date):

    truncated = df.merged[(df.merged['tran_date']>=start_date)&(df.merged['tran_date']<=end_date)]
    grouped = truncated[truncated['total_amt']>0].groupby([pd.Grouper(key='tran_date',freq='M'),'Store_type'])['total_amt'].sum().round(2).unstack()

    traces = []
    for col in grouped.columns:
        traces.append(go.Bar(x=grouped.index,y=grouped[col],name=col,hoverinfo='text',
        hovertext=[f'{y/1e3:.2f}k' for y in grouped[col].values]))

    data = traces
    fig = go.Figure(data=data,layout=go.Layout(title='Przychody',barmode='stack',legend=dict(x=0,y=-0.5)))

    return fig

@app.callback(Output('choropleth_sales','figure'),
            [Input('sales_range','start_date'),Input('sales_range','end_date')])
def tab1_choropleth_sales(start_date,end_date):

    truncated = df.merged[(df.merged['tran_date']>=start_date)&(df.merged['tran_date']<=end_date)]
    grouped = truncated[truncated['total_amt']>0].groupby('country')['total_amt'].sum().round(2)

    trace0 = go.Choropleth(colorscale='Viridis',reversescale=True,
                            locations=grouped.index,locationmode='country names',
                            z = grouped.values, colorbar=dict(title='Sales'))
    data = [trace0]
    fig = go.Figure(data=data,layout=go.Layout(title='Mapa',geo=dict(showframe=False,projection={'type':'natural earth'})))

    return fig

## tab2 callbacks
@app.callback(Output('barh_prod_subcat','figure'),
            [Input('prod_dropdown','value')])
def tab2_barh_prod_subcat(chosen_cat):

    grouped = df.merged[(df.merged['total_amt']>0)&(df.merged['prod_cat']==chosen_cat)].pivot_table(index='prod_subcat',columns='Gender',values='total_amt',aggfunc='sum').assign(_sum=lambda x: x['F']+x['M']).sort_values(by='_sum').round(2)

    traces = []
    for col in ['F','M']:
        traces.append(go.Bar(x=grouped[col],y=grouped.index,orientation='h',name=col))

    data = traces
    fig = go.Figure(data=data,layout=go.Layout(barmode='stack',margin={'t':20,}))
    return fig

## tab3 callbacks

@app.callback(Output('heatmap_store_type','figure'),
            [Input('heatmap_range','start_date'),Input('heatmap_range','end_date')])
def tab3_heatmap_store_type(start_date,end_date):

    truncated = df.merged[(df.merged['tran_date']>=start_date)&(df.merged['tran_date']<=end_date)]
    grouped = truncated[truncated['total_amt']>0].groupby([pd.Grouper(key='tran_date',freq='C'),'Store_type'])['total_amt'].sum().round(2).unstack()
    grouped = grouped.groupby(grouped.index.weekday).sum()

    trace0 = go.Heatmap(x=grouped.columns,
                        y=grouped.index.map({0:'Poniedziałek',1:'Wtorek',2:'Środa',3:'Czwartek',4:'Piątek',5:'Sobota',6:'Niedziela'}),
                        z=grouped.values)

    data = [trace0]
    fig = go.Figure(data=data,layout=go.Layout(title='Sprzedaż dla każdego z kanałów w danym dniu tygodnia'))

    return fig

@app.callback(Output('hist_store_type','figure'),
            [Input('store_dropdown','value')])
def tab3_heatmap_store_type(chosen_store):

    traces = []
    trace0 = go.Histogram(x=df.merged[(df.merged['Gender']=='M') & (df.merged['Store_type']==chosen_store)]['Age'],
                          name='mężczyźni', xbins=go.histogram.XBins(size=5))
    trace1 = go.Histogram(x=df.merged[(df.merged['Gender'] == 'F') & (df.merged['Store_type'] == chosen_store)]['Age'],
                          name='kobiety', xbins=go.histogram.XBins(size=5))
    traces.append(trace0)
    traces.append(trace1)

    data = traces
    fig = go.Figure(data=data,layout=go.Layout(title='Rozkład wieku klientów w zależności od płci',legend=dict(orientation='h', x=0, y=1.1),
                                               xaxis=dict(title='Wiek'), yaxis=dict(title='Częstotliwość')))
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)


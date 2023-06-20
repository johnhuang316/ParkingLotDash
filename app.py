from dotenv import load_dotenv
from dash import Dash, dcc, html, Input, Output, dash_table, State
import pandas as pd
import dash_bootstrap_components as dbc
from datastore.bigquerystorage import BigQueryStorage
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache
import plotly.express as px
import dash
import numpy as np


load_dotenv()
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)
storage = BigQueryStorage()
df = pd.DataFrame(storage.get_parking_lot_data())
app = Dash(__name__, long_callback_manager=long_callback_manager,external_stylesheets=[dbc.themes.BOOTSTRAP])
# server=app.server
all_options = {}
county_list = df['county'].dropna().unique().tolist()


graph=html.Div([
    dcc.Store(id='data-storage'),
    dcc.Dropdown(
        id='group-time',
        options=[
            {'label': '不分組', 'value': 'NO'},
            {'label': '小時', 'value': 'H'},
            {'label': '星期', 'value': 'W'},
            {'label': '星期小時', 'value': 'WH'},
            {'label': '平日假日小時', 'value': 'WDH'}
        ],
        value='NO'
    ),
    dcc.Dropdown(
        id='calc-method',
        options=[
            {'label': '平均', 'value': 'mean'},
            {'label': '最大', 'value': 'max'},
            {'label': '最小', 'value': 'min'}
        ],
        value='mean'
    ),
    dcc.Dropdown(
        id='chart-type',
        options=[
            {'label': '折線圖', 'value': 'line'},
            {'label': '長條圖', 'value': 'bar'},
            {'label': '箱型圖', 'value': 'box'},
            {'label': '散點圖', 'value': 'scatter'},
            {'label': '熱圖', 'value': 'heatmap'}
        ],
        value='line'
    ),
    dcc.Graph(id='graph')
])

info_card = dbc.Card(
    dbc.CardBody([
        html.H4(id='parking-lot-name', className="card-title"),
        html.H6(id='parking-lot-id',className="card-subtitle"),
        html.P(id='parking-lot-address',className="card-text"),
        html.H6('總停車位數',className="card-subtitle"),
        html.P(id='parking-lot-spaces',className="card-text"),
        html.P(id='parking-lot-description',className="card-text")
    ])
)

table = dash_table.DataTable(
    page_size=10,  
    style_cell={'textAlign': 'left', 'whiteSpace': 'normal'},
    id='tbl',
)

dropdown_list = [
    dbc.Row([
        dcc.Dropdown(
            county_list,
            county_list[0],
            id='county-dropdown',
            style={"margin-bottom": "2px"}
        ),
        dcc.Dropdown(id='district-dropdown', style={"margin-bottom": "2px"}),
        dcc.Dropdown(id='officialid-dropdown', style={"margin-bottom": "2px"}),
        dbc.Button("Submit", id="submit", className="me-2", n_clicks=0),
    ]),
    dbc.Row(
        [
            table,
            dbc.Spinner(color="primary",id='spinner',spinner_style={'display':'none'}),
        ]
    )
]

app.layout = dbc.Container([
    html.H1("停車空位記錄"),
    dbc.Container([
        dbc.Row([
            dbc.Col(dropdown_list, width=4),
            dbc.Col(info_card),
        ],style={"margin-bottom": "20px"}),
        dbc.Row(graph)
    ])
])

@app.callback(
    Output('district-dropdown', 'options'),
    Output('district-dropdown', 'value'),
    Input('county-dropdown', 'value'),
    Input('officialid-dropdown', 'value'),
)
def set_district_options(county,official_id):
    filter1 = df['county'] == county
    if official_id is not None or "":
        filter1 = filter1 & (df['official_id'] == official_id)
    district_list = df['district'].where(filter1).dropna().unique().tolist()
    options = [{'label': i, 'value': i}
               for i in list(filter(None, district_list))]
    value = ''
    if len(options)>0:
        value = options[0]['value']
    return options, value


@app.callback(
    Output('officialid-dropdown', 'options'),
    Input('district-dropdown', 'value'),
    Input('county-dropdown', 'value'),
)
def set_district_value(district, county):
    filter1 = df['county'] == county
    if district is not None or "":
        filter1 = filter1 & (df['district'] == district) & (df['district'] is not None)

    official_list = df.where(filter1).filter(items=['name', 'official_id']).dropna().to_dict('records')

    return [{'label': i['name'], 'value': i['official_id']} for i in official_list]


@app.callback(
    Output('district-dropdown', 'options', allow_duplicate=True),
    Input('officialid-dropdown', 'value'),
    Input('district-dropdown', 'options'),
    prevent_initial_call=True,
)
def set_official_id_value(official_id,district_options):
    if official_id is not None or "":
        filter1 = df['official_id'] == official_id
        district_list = df['district'].where(filter1).dropna().unique().tolist()
        options = [{'label': i, 'value': i}
               for i in list(filter(None, district_list))]
    else:
        options = district_options
    return options


@app.callback(
    Output('parking-lot-name', 'children'),
    Output('parking-lot-id', 'children'),
    Output('parking-lot-address', 'children'),
    Output('parking-lot-spaces', 'children'),
    Output('parking-lot-description', 'children'),
    Input('county-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('officialid-dropdown', 'value'))
def set_display_children(selected_county, selected_district, selected_official_id):
    filter1 = df['county'] == selected_county
    filter2 = df['district'] == selected_district
    filter3 = df['official_id'] == selected_official_id
    parking_lot = df.where(filter1 & filter2 & filter3).dropna().to_dict('records')
    if len(parking_lot) == 0:
        return '','','','',''
    parking_lot = parking_lot[0]
    total_spaces_string = f"""
    小客車:{parking_lot['total_parking_spaces']}
    \n
    摩托車:{parking_lot['total_motorcycle_spaces']}
    \n
    充電樁:{parking_lot['total_charging_stations']}
            """
    return parking_lot['name'],parking_lot['official_id'],f"地址:{parking_lot['address']}",total_spaces_string,parking_lot['description']

@app.long_callback(
    Output('data-storage', 'data'),
    inputs=[
        Input('submit', 'n_clicks'),
        State('county-dropdown', 'value'),
        State('officialid-dropdown', 'value'),
    ],
    running=[
        (Output("submit", "disabled"), True, False),
        (Output("tbl", "style_table"), {'display':'none'}, {'height': '150px', 'overflowY': 'auto'}),
        (Output("spinner", "spinner_style"), {'display':'block'}, {'display':'none'}),
    ],
    prevent_initial_call=True,
)
def load_data(n_clicks,selected_county, selected_official_id):
    print(n_clicks)
    data=pd.DataFrame(storage.get_parkig_time_data(selected_official_id,selected_county))
    return data.to_dict('records')


@app.callback(
    Output('graph', 'figure'),
    Output('tbl', 'data'),
    Output('tbl', 'columns'),
    Input('group-time', 'value'),
    Input('calc-method', 'value'),
    Input('chart-type', 'value'),
    Input('data-storage', 'data'),
    prevent_initial_call=True
)
def update_graph(group_time, calc_method, chart_type, data):
    if data is None:
        return dash.no_update

    data_frame = pd.DataFrame(data)
    
    columns=[{'id': c, 'name': c} for c in data_frame.columns]

    data_frame['time'] = pd.to_datetime(data_frame['time'])

    if group_time == 'NO':
        data_frame['time'] = data_frame['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        data_frame.index = data_frame['time']
        data_frame_grouped = data_frame
    else:
        # 更新分組的映射
        group_mapping = {
            'H': data_frame['time'].dt.hour,
            'W': data_frame['time'].dt.dayofweek,
            'WH': [data_frame['time'].dt.dayofweek, data_frame['time'].dt.hour],
            'WDH': [(data_frame['time'].dt.dayofweek < 5).astype(int), data_frame['time'].dt.hour]
        }
        agg_mapping = {
            'mean': np.mean,
            'max': np.max,
            'min': np.min
        }
            
        group_key = group_mapping[group_time]
        agg_func = agg_mapping[calc_method]
        data_frame_grouped = data_frame.groupby(group_key)['remaining_parking_spaces'].agg(agg_func)
        
        if isinstance(data_frame_grouped.index, pd.MultiIndex):
            data_frame_grouped.index = data_frame_grouped.index.to_flat_index().astype(str)
        
            
        weekday_map = {
            0: 'Monday',
            1: 'Tuesday',
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        
        # Convert the numeric weekday and hour labels to more human-readable ones
        if group_time == 'H':
            data_frame_grouped.index = data_frame_grouped.index.map(lambda x: f'{x}:00-{x+1}:00')
        elif group_time == 'W':
            data_frame_grouped.index = data_frame_grouped.index.map(weekday_map.get)
        elif group_time == 'WH':
            data_frame_grouped.index = data_frame_grouped.index.map(
                lambda x: f"{weekday_map[int(x.strip('() ').split(',')[0])]} {x.strip('() ').split(',')[1]}:00-{int(x.strip('() ').split(',')[1])+1}:00"
            )
        elif group_time == 'WDH':
            data_frame_grouped.index = data_frame_grouped.index.map(
                lambda x: f"{'週間' if int(x.strip('() ').split(',')[0]) == 0 else '週末'} {x.strip('() ').split(',')[1]}:00-{int(x.strip('() ').split(',')[1])+1}:00"
            )


    chart_mapping = {
        'line': px.line,
        'bar': px.bar,
        'box': px.box,
        'scatter': px.scatter,
        'heatmap': px.density_heatmap
    }
    chart_func = chart_mapping[chart_type]
    
        
    if chart_type == 'heatmap':
        fig = chart_func(data_frame_grouped, x=data_frame_grouped.index, y='remaining_parking_spaces', nbinsx=20)
    else:
        fig = chart_func(data_frame_grouped, x=data_frame_grouped.index, y='remaining_parking_spaces')
        
    return fig, data, columns


    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8050", debug=False)

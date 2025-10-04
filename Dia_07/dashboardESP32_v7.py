import os
from flask import Flask
import requests
from collections import deque
from datetime import datetime
import pandas as pd
import dash
from dash import dcc, html, Input, Output, ctx
import plotly.graph_objects as go
import sqlite3
from usuarios import VerificaUsuario

# ----------------------------
# Configuração
# ----------------------------
server = Flask(__name__)
esp32_ip = os.getenv("ESP32_IP", "172.30.92.158")
data_history = deque(maxlen=100)
last_update = None
connection_status = "Desconectado"
DATABASE_NAME = "sensor_data.db"
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSf0DGncBYg6IJwhoB0PEX4PIh1XsZj1OUcVpGKHGoSgDNgN1w/formResponse?&submit=Submit?usp=pp_url&"

# ----------------------------
# Funções de Banco de Dados SQLite
# ----------------------------
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            timestamp TEXT PRIMARY KEY,
            temperatura REAL,
            umidade REAL,
            tensao REAL,
            botao INTEGER,
            motor INTEGER,
            alarme INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(data_with_time):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO sensor_readings (timestamp, temperatura, umidade, tensao, botao, motor, alarme)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data_with_time["timestamp"].isoformat(),
            data_with_time.get("temperatura"),
            data_with_time.get("umidade"),
            data_with_time.get("tensao"),
            data_with_time.get("botao"),
            data_with_time.get("motor"),
            data_with_time.get("alarme")
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Erro: Entrada duplicada para o timestamp {data_with_time['timestamp']}. Ignorando.")
    finally:
        conn.close()

def get_data_from_db():
    conn = sqlite3.connect(DATABASE_NAME)
    df = pd.read_sql_query("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 100", conn)
    conn.close()
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

# ----------------------------
# Funções de Comunicação
# ----------------------------
class ESP32Controller:
    def __init__(self, ip_address):
        self.ip = ip_address
        self.base_url = f"http://{ip_address}"

    def get_sensor_data(self):
        try:
            response = requests.get(self.base_url, timeout=5)
            response.raise_for_status()
            if "application/json" in response.headers.get("Content-Type", ""):
                data = response.json()
                return data[0] if isinstance(data, list) and data else None
            return None
        except requests.exceptions.RequestException:
            return None

    def control_motor(self, action: str):
        endpoint = "/motor1_h" if action == "ligar" else "/motor1_l"
        return self._send_command(endpoint)

    def control_alarm(self, action: str):
        endpoint = "/alarme_h" if action == "ligar" else "/alarme_l"
        return self._send_command(endpoint)

    def control_clp(self, action: str):
        endpoint = "/pulsoCLP" if action == "ligar" else "/alarme_h" # Assumindo que 'alarme_l' é o estado 'desligar' para o CLP, ou ajuste conforme necessário
        return self._send_command(endpoint)


    def _send_command(self, endpoint: str):
        try:
            r = requests.get(f"{self.base_url}{endpoint}", timeout=3)
            return r.status_code == 200
        except requests.exceptions.RequestException:
            return False

def send_data_to_google_form(data: dict):
    if not data:
        return False
    try:
        params = {
            'entry.1518093638': data.get('Temperatura'),
            'entry.1621899341': data.get('Umidade'),
            'entry.1262249026': data.get('Botao'),
            'entry.1332691306': data.get('Alarme'),
            'entry.YOUR_TENSION_ENTRY_ID': data.get('Tensao'),
            'submit': 'Submit'
        }
        response = requests.get(GOOGLE_FORM_URL, params=params, timeout=3)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

init_db()
esp32 = ESP32Controller(esp32_ip)

# ----------------------------
# Funções Auxiliares do Dash
# ----------------------------
def update_data_history(data):
    global last_update, connection_status
    if data:
        timestamp = datetime.now()
        data_with_time = {
            'timestamp': timestamp,
            'temperatura': data.get('Temperatura'),
            'umidade': data.get('Umidade'),
            'tensao': data.get('Tensao'),
            'botao': data.get('Botao', 0),
            'motor': data.get('Motor', 0),
            'alarme': data.get('Alarme', 0)
        }
        data_history.append(data_with_time)
        save_to_db(data_with_time)
        last_update = timestamp
        connection_status = "Conectado"
    else:
        connection_status = "Falha na conexão"

def create_temperature_humidity_chart():
    if not data_history: return go.Figure()
    df = pd.DataFrame(list(data_history)).dropna(subset=['temperatura', 'umidade'])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['temperatura'], mode='lines+markers', name='Temperatura (°C)', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['umidade'], mode='lines+markers', name='Umidade (%)', line=dict(color='blue'), yaxis="y2"))
    fig.update_layout(title="Histórico de Temperatura e Umidade", xaxis_title="Tempo", yaxis=dict(title='Temperatura (°C)'), yaxis2=dict(title='Umidade (%)', overlaying='y', side='right'), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ----------------------------
# Layout do Dash App
# ----------------------------
app = dash.Dash(__name__, server=server, url_base_pathname="/")
app.layout = html.Div([
    html.H1("Painel de Controle ESP32"),
    dcc.Tabs(id="tabs-main", value='tab-realtime', children=[
        dcc.Tab(label='Monitoramento em Tempo Real', value='tab-realtime'),
        dcc.Tab(label='Dados Históricos (SQLite)', value='tab-historical'),
    ]),
    html.Div(id='tabs-content')
])

# ----------------------------
# Callbacks
# ----------------------------
@app.callback(Output('tabs-content', 'children'),
              Input('tabs-main', 'value'))
def render_content(tab):
    if tab == 'tab-realtime':
        return html.Div([
            dcc.Loading(id="loading-icon", type="default", children=[
                html.Div(id="status-connection", style={"margin": "10px 0"}),
                html.Div(id="current-data"),
            ]),
            html.Button("Atualizar Dados", id="btn-update", n_clicks=0),
            html.Button("Limpar Gráficos", id="btn-clear-graphs", n_clicks=0, style={'marginLeft': '10px'}),
            dcc.Interval(id="auto-update", interval=5000, n_intervals=0),
            dcc.Graph(id="temp-hum-graph"),
            html.H3("Controles"),
            html.Button("Ligar Motor", id="btn-motor-on", n_clicks=0),
            html.Button("Desligar Motor", id="btn-motor-off", n_clicks=0),
            html.Button("Ativar Alarme", id="btn-alarm-on", n_clicks=0),
            html.Button("Desativar Alarme", id="btn-alarm-off", n_clicks=0),
            html.Button("Ativar IA", id="btn-IA-on", n_clicks=0, style={'marginLeft': '10px'}),
            html.H3("Dados Recentes (últimos 10)"),
            html.Div(id="recent-data-table"),
        ])
    elif tab == 'tab-historical':
        return html.Div([
            html.H3('Histórico de Dados do Banco de Dados'),
            dcc.Graph(id='historical-graph'),
            html.Div(id='historical-table')
        ])

@app.callback(
    Output("temp-hum-graph", "figure"),
    Output("current-data", "children"),
    Output("status-connection", "children"),
    Output("recent-data-table", "children"),
    Input("btn-update", "n_clicks"),
    Input("auto-update", "n_intervals"),
    Input("btn-motor-on", "n_clicks"),
    Input("btn-motor-off", "n_clicks"),
    Input("btn-alarm-on", "n_clicks"),
    Input("btn-alarm-off", "n_clicks"),
    Input("btn-clear-graphs", "n_clicks"),
    Input("btn-IA-on", "n_clicks"),
    prevent_initial_call=False
)
def update_realtime_dashboard(n_update, n_interval, m_on, m_off, a_on, a_off, n_clear, ia_on):
    global connection_status, data_history
    triggered_id = ctx.triggered_id if ctx.triggered_id else 'auto-update'

    if triggered_id == "btn-clear-graphs":
        data_history.clear()
        return create_temperature_humidity_chart(), html.P("Histórico limpo."), "Histórico limpo.", html.P("Sem dados.")

    if triggered_id.startswith("btn-"):
        if triggered_id == "btn-motor-on":
            connection_status = "Motor ligado" if esp32.control_motor("ligar") else "Falha ao ligar motor"
        elif triggered_id == "btn-motor-off":
            connection_status = "Motor desligado" if esp32.control_motor("desligar") else "Falha ao desligar motor"
        elif triggered_id == "btn-alarm-on":
            connection_status = "Alarme ativado" if esp32.control_alarm("ligar") else "Falha ao ativar alarme"
        elif triggered_id == "btn-alarm-off":
            connection_status = "Alarme desativado" if esp32.control_alarm("desligar") else "Falha ao desativar alarme"
        elif triggered_id == "btn-IA-on":
            connection_status = "Verificando usuário com IA..."
            if VerificaUsuario():
                connection_status = "Ativado" if esp32.control_clp("ligar") else "Falha ao Ativar"
            else:
                connection_status = "Usuário não verificado."

    data = esp32.get_sensor_data()
    update_data_history(data)

    if data:
        google_success = send_data_to_google_form(data)
        if google_success:
            connection_status = "Conectado e Dados Enviados para o Google"
        else:
            connection_status = "Conectado, mas falha ao enviar para o Google"

    fig = create_temperature_humidity_chart()
    
    if data_history:
        last_data = data_history[-1]
        current = [
            html.P(f"Temperatura: {last_data['temperatura']:.1f} °C" if last_data.get('temperatura') is not None else "Temperatura: N/A"),
            html.P(f"Umidade: {last_data['umidade']:.1f} %" if last_data.get('umidade') is not None else "Umidade: N/A"),
            html.P(f"Tensão: {last_data['tensao']:.2f} V" if last_data.get('tensao') is not None else "Tensão: N/A"),
            html.P(f"Botão: {'Pressionado' if last_data['botao'] else 'Solto'}"),
            html.P(f"Motor: {'Ligado' if last_data['motor'] else 'Desligado'}"),
            html.P(f"Alarme: {'Ativo' if last_data['alarme'] else 'Inativo'}")
        ]
        df = pd.DataFrame(list(data_history)); df['timestamp'] = df['timestamp'].dt.strftime("%H:%M:%S"); df = df.tail(10).iloc[::-1]
        table = html.Table([html.Thead(html.Tr([html.Th(col) for col in df.columns])), html.Tbody([html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))])], style={'width': '100%', 'textAlign': 'center'})
    else:
        current = [html.P("Sem dados do ESP32")]
        table = html.P("Sem histórico de dados.")

    status_msg = f"{connection_status}"
    if last_update:
        status_msg += f" | Última atualização: {last_update.strftime('%H:%M:%S')}"

    return fig, current, status_msg, table

@app.callback(
    Output("historical-graph", "figure"),
    Output("historical-table", "children"),
    Input("tabs-main", "value")
)
def update_historical_tab(tab):
    if tab == 'tab-historical':
        df = get_data_from_db()
        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['temperatura'], mode='lines+markers', name='Temperatura (°C)', line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df['timestamp'], y=df['umidade'], mode='lines+markers', name='Umidade (%)', line=dict(color='blue'), yaxis="y2"))
            fig.update_layout(title="Histórico de Temperatura e Umidade (SQLite)", xaxis_title="Tempo", yaxis=dict(title='Temperatura (°C)'), yaxis2=dict(title='Umidade (%)', overlaying='y', side='right'), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            
            df['timestamp'] = df['timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")
            table = html.Table([html.Thead(html.Tr([html.Th(col) for col in df.columns])), html.Tbody([html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))])], style={'width': '100%', 'textAlign': 'center'})
            return fig, table
        else:
            return go.Figure(), html.P("Sem dados históricos no banco de dados.")
    return go.Figure(), html.Div()

# ----------------------------
# Rodar servidor
# ----------------------------
if __name__ == "__main__":
    app.run(debug=False, port=8050)


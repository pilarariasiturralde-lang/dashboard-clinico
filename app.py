import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd
import plotly.express as px

# =========================
# CARGA Y LIMPIEZA
# =========================
df = pd.read_csv("clinical_analytics.csv.gz", compression="gzip")

df["Appt Start Time"] = pd.to_datetime(df["Appt Start Time"], errors="coerce")
df["Discharge Datetime new"] = pd.to_datetime(df["Discharge Datetime new"], errors="coerce")

df["Diagnosis Primary"] = df["Diagnosis Primary"].fillna("Unknown")
df["Encounter Status"] = df["Encounter Status"].fillna("Desconocido")

df["Duracion_min"] = (
    df["Discharge Datetime new"] - df["Appt Start Time"]
).dt.total_seconds() / 60

df = df[(df["Duracion_min"] >= 0) & (df["Duracion_min"] <= 43200)]

# =========================
# APP
# =========================
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
server = app.server

app.layout = dbc.Container([

    html.H2("Dashboard Clínico"),

    # FILTROS
    dbc.Row([
        dbc.Col(dcc.Dropdown(
            options=[{"label": i, "value": i} for i in df["Department"].dropna().unique()],
            multi=True, placeholder="Departamento", id="dep"
        ), width=4),

        dbc.Col(dcc.Dropdown(
            options=[{"label": i, "value": i} for i in df["Encounter Status"].dropna().unique()],
            multi=True, placeholder="Estado", id="status"
        ), width=4),

        dbc.Col(dcc.DatePickerRange(
            start_date=df["Appt Start Time"].min(),
            end_date=df["Appt Start Time"].max(),
            id="fecha"
        ), width=4)
    ], className="mb-4"),

    # KPIs
    dbc.Row([

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Tiempo Promedio de Atención"),
                html.H4(id="kpi_tiempo", style={"color": "#2c7be5"})
            ])
        ]), width=4),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("Total Registros"),
                html.H4(id="kpi_total")
            ])
        ]), width=4),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("% Atenciones Canceladas"),
                html.H4(id="kpi_cancel", style={"color": "red"})
            ])
        ]), width=4),

    ], className="mb-4"),

    # TABS
    dbc.Tabs(id="tabs", children=[
        dbc.Tab(label="Tiempos", tab_id="tab1"),
        dbc.Tab(label="Ingresos", tab_id="tab2"),
        dbc.Tab(label="Calidad", tab_id="tab3"),
        dbc.Tab(label="Diagnósticos", tab_id="tab4"),
        dbc.Tab(label="Volumen", tab_id="tab5"),
    ]),

    html.Div(id="contenido")

], fluid=True)

# =========================
# CALLBACK
# =========================
@app.callback(
    Output("contenido", "children"),
    Output("kpi_tiempo", "children"),
    Output("kpi_total", "children"),
    Output("kpi_cancel", "children"),
    Input("tabs", "active_tab"),
    Input("dep", "value"),
    Input("status", "value"),
    Input("fecha", "start_date"),
    Input("fecha", "end_date")
)
def render(tab, dep, status, start, end):

    dff = df.copy()

    # filtros principales
    if dep:
        dff = dff[dff["Department"].isin(dep)]

    if status:
        dff = dff[dff["Encounter Status"].isin(status)]

    dff = dff[
        (dff["Appt Start Time"] >= start) &
        (dff["Appt Start Time"] <= end)
    ]

    if dff.empty:
        return html.Div("No hay datos"), "-", "-", "-"

    # =========================
    # KPI CORRECTO (sin sesgo por estado)
    # =========================
    dff_base = df.copy()

    if dep:
        dff_base = dff_base[dff_base["Department"].isin(dep)]

    dff_base = dff_base[
        (dff_base["Appt Start Time"] >= start) &
        (dff_base["Appt Start Time"] <= end)
    ]

    promedio = dff["Duracion_min"].mean()
    total = len(dff)

    cancel = dff["Encounter Status"].str.strip().str.lower().eq("cancelled").sum()
    total = len(dff)

    porc_cancel = (cancel / total * 100) if total > 0 else 0

    # KPI en días
    kpi_tiempo = f"{int(promedio//1440)}d {int((promedio%1440)//60)}h {int(promedio%60)}m"
    kpi_total = str(total)
    kpi_cancel = f"{cancel} ({porc_cancel:.3f}%)"

    # =========================
    # TAB 1 TIEMPOS
    # =========================
    if tab == "tab1":

        df_time = dff.copy()

        if df_time.empty:
            return html.Div("No hay datos"), "-", "-", "-"

        # promedio por departamento
        df_group = df_time.groupby("Department")["Duracion_min"].mean().reset_index()
        df_group = df_group.sort_values("Duracion_min", ascending=False)

        # texto en días/horas/min
        df_group["Duracion_txt"] = df_group["Duracion_min"].apply(
            lambda x: f"{int(x//1440)}d {int((x%1440)//60)}h {int(x%60)}m"
        )

        # gráfico
        fig = px.bar(
            df_group,
            x="Department",
            y="Duracion_min",
            text="Duracion_txt",
            title="Tiempo promedio de atención por Departamento"
        )

        fig.update_traces(
            texttemplate='%{text}',
            textposition='outside',
        )

        fig.update_layout(
            height=600,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title="Departamento",
            yaxis_title="Promedio de Atención",
            margin=dict(l=150, r=40, t=60, b=40)
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS
        # =========================
        mayor = df_group.iloc[0]
        menor = df_group.iloc[-1]

        promedio_global = df_time["Duracion_min"].mean()

        # variabilidad
        diferencia = mayor["Duracion_min"] - menor["Duracion_min"]

        insights = html.Div([

            html.H5("Insights automáticos"),

            html.Ul([
                html.Li(f"El departamento con mayor tiempo promedio es '{mayor['Department']}' con {mayor['Duracion_txt']}."),
                html.Li(f"El menor tiempo se observa en '{menor['Department']}' con {menor['Duracion_txt']}."),
                html.Li(f"El tiempo promedio general es {int(promedio_global//1440)}d {int((promedio_global%1440)//60)}h."),
                html.Li(f"La diferencia entre el mayor y menor tiempo es significativa ({int(diferencia//60)} horas).")
            ]),

            html.P(
                "Se observan diferencias importantes en los tiempos de atención entre departamentos, lo que puede indicar ineficiencias operativas o variabilidad en la complejidad de los casos."
            )

        ], style={
            "backgroundColor": "#f8f9fa",
            "padding": "15px",
            "borderRadius": "10px"
        })

        # =========================
        # LAYOUT
        # =========================
        return html.Div([

            dbc.Row([

                dbc.Col(dcc.Graph(figure=fig), width=8),

                dbc.Col(insights, width=4)

            ])

        ]), kpi_tiempo, kpi_total, kpi_cancel

    # =========================
    # TAB 2 INGRESOS
    # =========================
    elif tab == "tab2":

        df_ing = dff.copy()

        df_ing = df_ing.dropna(subset=["Admit Type"])

        if df_ing.empty:
            return html.Div("No hay datos"), kpi_tiempo, kpi_total, kpi_cancel

        # conteo
        df_count = df_ing["Admit Type"].value_counts().reset_index()
        df_count.columns = ["Admit Type", "Total"]

        # porcentaje
        total = df_count["Total"].sum()
        df_count["Porcentaje"] = df_count["Total"] / total * 100

        # gráfico
        fig = px.bar(
            df_count,
            x="Admit Type",
            y="Total",
            text="Total",
            title="Tipos de ingreso"
        )

        fig.update_traces(textposition="inside")

        fig.update_layout(
            height=350,
            xaxis_title="Tipo de ingreso",
            yaxis_title="Número de atenciones"
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS
        # =========================
        top = df_count.iloc[0]
        low = df_count.iloc[-1]

        insights = html.Div([

            html.H5("Insights automáticos"),

            html.Ul([
                html.Li(f"El tipo de ingreso más frecuente es '{top['Admit Type']}' con {top['Total']} atenciones ({top['Porcentaje']:.1f}%)."),
                html.Li(f"El tipo menos frecuente es '{low['Admit Type']}' con {low['Total']} atenciones ({low['Porcentaje']:.1f}%)."),
                html.Li(f"Total de atenciones analizadas: {int(total)}.")
            ]),

            html.P(
                "Se observa concentración en ciertos tipos de ingreso, lo que puede indicar dependencia operativa."
            )

        ], style={
            "backgroundColor": "#f8f9fa",
            "padding": "15px",
            "borderRadius": "10px"
        })

        # =========================
        # LAYOUT
        # =========================
        return html.Div([

            dbc.Row([

                dbc.Col(dcc.Graph(figure=fig), width=8),

                dbc.Col(insights, width=4)

            ])

        ]), kpi_tiempo, kpi_total, kpi_cancel

    # =========================
    # TAB 3 CALIDAD POR CLINICA
    # =========================
    elif tab == "tab3":

        df_cal = dff.copy()

        # limpiar
        df_cal["Care Score"] = pd.to_numeric(df_cal["Care Score"], errors="coerce")
        df_cal = df_cal.dropna(subset=["Care Score", "Clinic Name"])

        if df_cal.empty:
            return html.Div("No hay datos"), kpi_tiempo, kpi_total, kpi_cancel

        # promedio por clínica
        df_avg = df_cal.groupby("Clinic Name")["Care Score"].mean().reset_index()

        # ordenar
        df_avg = df_avg.sort_values("Care Score", ascending=False)

        # =========================
        # CLASIFICACIÓN
        # =========================
        def clasificar(score):
            if score < 5:
                return "Baja"
            elif score < 8:
                return "Media"
            else:
                return "Alta"

        def estado_sistema(score):
            if score < 5:
                return "CRÍTICO", "#dc3545"
            elif score < 8:
                return "ACEPTABLE", "#ffc107"
            else:
                return "ÓPTIMO", "#198754"

        df_avg["Nivel"] = df_avg["Care Score"].apply(clasificar)

        # =========================
        # GRÁFICO
        # =========================
        fig = px.bar(
            df_avg,
            x="Clinic Name",
            y="Care Score",
            color="Nivel",
            text="Care Score",
            title="Calidad promedio por clínica",
            color_discrete_map={
                "Alta": "#198754",   # verde
                "Media": "#ffc107",  # naranja
                "Baja": "#dc3545"    # rojo
            }
        )

        # texto dentro para no romper layout
        fig.update_traces(
            texttemplate='%{text:.2f}',
            textposition='inside'
        )

        # altura controlada
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=40),
            xaxis_title="Clínica",
            yaxis_title="Promedio Care Score",
            xaxis_tickangle=-45
        )
        # =========================
        # KPIs INTERNOS
        # =========================
        mejor = df_avg.iloc[0]
        peor = df_avg.iloc[-1]

        promedio_global = df_cal["Care Score"].mean()
        nivel_global = clasificar(promedio_global)
        estado, color = estado_sistema(promedio_global)

        # =========================
        # SEMÁFORO DEL SISTEMA
        # =========================
        return html.Div([
            html.Div([
                html.H4(
                    f"Estado del sistema: {estado}",
                    style={
                        "color": "white",
                        "backgroundColor": color,
                        "padding": "12px",
                        "borderRadius": "8px",
                        "textAlign": "center"
                    }
                )
            ], style={"marginBottom": "20px"}),

            # LAYOUT
            dbc.Row([

                # GRÁFICO
            dbc.Col(
                dcc.Graph(figure=fig),
                width=8
            ),

            # INSIGHTS
            dbc.Col([

                html.H5("Insights automáticos"),

                html.Div([

                    html.P("Escala de calidad:"),
                    html.P("🔴 Baja (1–4)"),
                    html.P("🟡 Media (5–7)"),
                    html.P("🟢 Alta (8–10)"),

                    html.Hr(),

                    html.Ul([
                        html.Li(f"Mejor clínica: {mejor['Clinic Name']} ({mejor['Care Score']:.2f}) → {clasificar(mejor['Care Score'])}"),
                        html.Li(f"Peor clínica: {peor['Clinic Name']} ({peor['Care Score']:.2f}) → {clasificar(peor['Care Score'])}"),
                        html.Li(f"Promedio general: {promedio_global:.2f} → {nivel_global}")
                    ]),

                    html.Hr(),

                    html.P(
                        "🔴 El sistema presenta un nivel CRÍTICO de calidad. Requiere intervención inmediata."
                        if estado == "CRÍTICO" else
                        "🟡 El sistema es ACEPTABLE pero requiere mejoras."
                        if estado == "ACEPTABLE" else
                        "🟢 El sistema presenta un nivel ÓPTIMO de calidad."
                    )

                ], style={
                    "backgroundColor": "#f8f9fa",
                    "padding": "15px",
                    "borderRadius": "10px"
                })

            ], width=4)

        ])

    ]), kpi_tiempo, kpi_total, kpi_cancel
        

           
    # =========================
    # TAB 4 ATENCIONES POR DIAGNOSTICOS
    # =========================
    elif tab == "tab4":

        df_diag = dff.copy()

        # limpiar
        df_diag = df_diag.dropna(subset=["Diagnosis Primary", "Admit Source"])

        if df_diag.empty:
            return html.Div("No hay datos"), kpi_tiempo, kpi_total, kpi_cancel

        # contar
        df_group = (
            df_diag.groupby(["Diagnosis Primary", "Admit Source"])
            .size()
            .reset_index(name="Total")
        )

        # TOP 10 diagnósticos
        top_diag = (
            df_group.groupby("Diagnosis Primary")["Total"]
            .sum()
            .nlargest(10)
            .index
        )

        df_group = df_group[df_group["Diagnosis Primary"].isin(top_diag)]

        # porcentaje dentro de cada origen
        df_group["Porcentaje"] = df_group.groupby("Admit Source")["Total"]\
            .transform(lambda x: x / x.sum() * 100)

        # eliminar ruido
        df_group = df_group[df_group["Porcentaje"] > 2]

        # acortar nombres
        df_group["Diagnosis Primary"] = df_group["Diagnosis Primary"].str.slice(0, 25)

        # pivot
        pivot = df_group.pivot(
            index="Diagnosis Primary",
            columns="Admit Source",
            values="Porcentaje"
        ).fillna(0)

        # gráfico heatmap
        fig = px.imshow(
            pivot,
            text_auto=".1f",
            aspect="auto",
            color_continuous_scale="Blues",
            title="Distribución (%) de diagnósticos por origen"
        )

        # mejoras visuales
        fig.update_traces(
            texttemplate="%{z:.1f}",
            textfont={"size": 11}
        )

        fig.update_layout(
            height=500,
            margin=dict(l=180, r=40, t=60, b=100),
            xaxis=dict(
                tickangle=0,
                tickfont=dict(size=10)
            ),
            xaxis_title="Origen de ingreso",
            yaxis_title="Diagnóstico"
        )

        # =========================
        # INSIGHT AUTOMÁTICO
        # =========================
        insights = []

        if not pivot.empty:
            for col in pivot.columns:
                if pivot[col].sum() > 0:
                    top_diag = pivot[col].idxmax()
                    top_val = pivot[col].max()

                    insights.append(
                        f"En {col}, el diagnóstico más frecuente es '{top_diag}' con {top_val:.1f}%."
                    )

        if insights:
            insight_text = html.Ul([html.Li(i) for i in insights])
        else:
            insight_text = html.P("No hay patrones suficientes para generar insights.")
        return html.Div([
            dcc.Graph(figure=fig),
            html.H5("Insights automáticos"),
            insight_text
        ]), kpi_tiempo, kpi_total, kpi_cancel
        

    # =========================
    # TAB 5 VOLUMEN
    # =========================
    elif tab == "tab5":

        df_vol = dff.copy()

        # FILTRO ESTRICTO SOLO 2014
        df_vol = df_vol[
            (df_vol["Appt Start Time"].dt.year == 2014)
        ]

        # agrupar por mes real (fecha)
        df_vol["Mes"] = df_vol["Appt Start Time"].dt.to_period("M").dt.to_timestamp()

        df_vol = df_vol.groupby("Mes").size().reset_index(name="Total")

        # gráfico
        fig = px.line(
            df_vol,
            x="Mes",
            y="Total",
            markers=True,
            text="Total",
            title="Tendencia mensual de atenciones"
        )

        fig.update_traces(textposition="top center")

        fig.update_layout(
            xaxis_title="Mes",
            yaxis_title="Número de atenciones"
        )

        # =========================
        # INSIGHT AUTOMÁTICO
        # =========================
        if not df_vol.empty:
            max_mes = df_vol.loc[df_vol["Total"].idxmax()]
            min_mes = df_vol.loc[df_vol["Total"].idxmin()]

            insight = html.Ul([
                html.Li(f"El mes con mayor volumen en atenciones fue {max_mes['Mes'].strftime('%Y-%m')} con {max_mes['Total']} atenciones."),
                html.Li(f"El mes con menor volumen en atenciones fue {min_mes['Mes'].strftime('%Y-%m')} con {min_mes['Total']} atenciones.")
            ])
        else:
            insight = html.P("No hay datos suficientes.")

        return html.Div([
            dcc.Graph(figure=fig),
            html.H5("Insights automáticos"),
            insight
        ]), kpi_tiempo, kpi_total, kpi_cancel

    # fallback obligatorio
        return html.Div("Seleccione una opción"), kpi_tiempo, kpi_total, kpi_cancel


    # =========================
    # RUN
    # =========================
if __name__ == "__main__":
        print("LLEGUE AL FINAL")
        app.run(debug=True, port=8050)
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd
import plotly.express as px

# =========================
# CONFIG
# =========================
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.LUX,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css"
    ]
)
server = app.server

# =========================
# CARGA DE DATOS
# =========================
df = pd.read_csv("clinical_analytics.csv.gz", compression="gzip")

# IMPORTANTE: COPIA ORIGINAL
df_original = df.copy()

df["Appt Start Time"] = pd.to_datetime(df["Appt Start Time"], errors="coerce")
df["Discharge Datetime new"] = pd.to_datetime(df["Discharge Datetime new"], errors="coerce")

df["Duracion_min"] = (
    df["Discharge Datetime new"] - df["Appt Start Time"]
).dt.total_seconds() / 60

df = df[(df["Duracion_min"] >= 0) & (df["Duracion_min"] <= 43200)]

df["Department"] = df["Department"].fillna("Unknown")
df["Encounter Status"] = df["Encounter Status"].fillna("Unknown")
df["Diagnosis Primary"] = df["Diagnosis Primary"].fillna("Unknown")

# =========================
# KPI
# =========================
def kpi(icon, title, value, color, extra):
    return dbc.Card(
        dbc.CardBody([
            html.I(className=icon, style={"fontSize": "28px", "color": color}),
            html.H6(title, className="text-muted mt-2"),
            html.H2(value, style={"fontWeight": "bold"}),
            html.Small(extra, style={"color": color})
        ]),
        style={"borderRadius": "12px", "boxShadow": "0 4px 12px rgba(0,0,0,0.1)"}
    )

# =========================
# LAYOUT
# =========================
app.layout = dbc.Container([

    html.Div([
        html.H2("DASHBOARD CLÍNICO"),
        html.P("Análisis de Tiempos, Ingresos, Calidad, Diagnósticos y Volumen de atenciones médicas")
    ], style={
        "background": "#0d6efd",
        "color": "white",
        "padding": "15px",
        "borderRadius": "10px",
        "marginBottom": "20px"
    }),

    dbc.Row([
        dbc.Col(dcc.Dropdown(
            options=[{"label": i, "value": i} for i in sorted(df["Department"].unique())],
            multi=True, placeholder="Departamento", id="dep"
        )),
        dbc.Col(dcc.Dropdown(
            options=[{"label": i, "value": i} for i in sorted(df["Encounter Status"].unique())],
            multi=True, placeholder="Estado", id="status"
        )),
        dbc.Col(dcc.DatePickerRange(
            start_date=df["Appt Start Time"].min(),
            end_date=df["Appt Start Time"].max(),
            id="fecha"
        ))
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(html.Div(id="kpi1"), width=4),
        dbc.Col(html.Div(id="kpi2"), width=4),
        dbc.Col(html.Div(id="kpi3"), width=4),
    ], className="g-4 mb-4"),

    dbc.Tabs([
        dbc.Tab(label="⏱ Tiempos", tab_id="tab1"),
        dbc.Tab(label="📥 Ingresos", tab_id="tab2"),
        dbc.Tab(label="⭐ Calidad", tab_id="tab3"),
        dbc.Tab(label="🧠 Diagnósticos", tab_id="tab4"),
        dbc.Tab(label="📈 Volumen", tab_id="tab5"),
    ], id="tabs", active_tab="tab1"),

    html.Div(id="contenido")

], fluid=True, style={"backgroundColor": "#f4f6f9", "padding": "20px"})

# =========================
# CALLBACK
# =========================
@app.callback(
    Output("contenido", "children"),
    Output("kpi1", "children"),
    Output("kpi2", "children"),
    Output("kpi3", "children"),
    Input("tabs", "active_tab"),
    Input("dep", "value"),
    Input("status", "value"),
    Input("fecha", "start_date"),
    Input("fecha", "end_date")
)
def update(tab, dep, status, start, end):

    dff = df.copy()

    if dep:
        dff = dff[dff["Department"].isin(dep)]
    if status:
        dff = dff[dff["Encounter Status"].isin(status)]

    dff = dff[
        (dff["Appt Start Time"] >= pd.to_datetime(start)) &
        (dff["Appt Start Time"] <= pd.to_datetime(end))
    ]

    if dff.empty:
        return "Sin datos", "-", "-", "-"

    dff["Check-In Time"] = pd.to_datetime(dff["Check-In Time"], errors="coerce")

    dff["Wait_real"] = (
        dff["Appt Start Time"] - dff["Check-In Time"]
    ).dt.total_seconds() / 60

    dff = dff[dff["Wait_real"].notna()]
    dff = dff[dff["Wait_real"] >= 0]

    # =========================
    # KPI CALCULOS
    # =========================
    promedio = dff["Wait_real"].mean()
    sla = (dff["Wait_real"] <= 60).mean() * 100

    total_real = len(df_original)

    cancel = dff["Encounter Status"].str.lower().eq("cancelled").sum()
    pct = cancel / len(dff) * 100 if len(dff) else 0

    # =========================
    # FORMATO TIEMPO
    # =========================
    def fmt(x):
        h = int(x // 60)
        m = int(x % 60)
        return f"{h}h {m}m"

    # =========================
    # KPIs
    # =========================
    k1 = kpi(
        "bi bi-clock",
        "Tiempo Espera Promedio",
        fmt(promedio),
        "#dc3545" if promedio > 120 else "#198754",
        "Alto" if promedio > 120 else "Normal"
    )

    k2 = kpi(
        "bi bi-database",
        "Total Atenciones",
        f"{total_real:,}",
        "#198754",
        "Global"
    )

    k3 = kpi(
        "bi bi-check-circle",
        "Pacientes atendidos ≤ 60 min",
        f"{sla:.1f}%",
        "#198754" if sla >= 80 else "#ffc107",
        "Óptimo" if sla >= 80 else "Mejorable"
    )

    # =========================
    # TAB 1 TIEMPOS DE ESPERA
    # =========================
    if tab == "tab1":

        try:
            df_t = df_original.copy()

            # =========================
            # FECHAS
            # =========================
            df_t["Check-In Time"] = pd.to_datetime(df_t["Check-In Time"], errors="coerce")
            df_t["Appt Start Time"] = pd.to_datetime(df_t["Appt Start Time"], errors="coerce")

            # =========================
            # TIEMPO DE ESPERA REAL (min)
            # =========================
            df_t["Wait_real"] = (
                df_t["Appt Start Time"] - df_t["Check-In Time"]
            ).dt.total_seconds() / 60

            # limpiar datos inválidos
            df_t = df_t[df_t["Wait_real"].notna()]
            df_t = df_t[df_t["Wait_real"] >= 0]

            if df_t.empty:
                return html.Div("No hay datos válidos para calcular tiempos."), k1, k2, k3

            # =========================
            # AGRUPACIÓN
            # =========================
            df_dep = df_t.groupby("Department").agg(
                Promedio=("Wait_real", "mean"),
                P90=("Wait_real", lambda x: x.quantile(0.9)),
                Total=("Wait_real", "count"),
                SLA=("Wait_real", lambda x: (x <= 60).mean() * 100)
            ).reset_index()

            df_dep = df_dep.sort_values("Promedio", ascending=False)

            # =========================
            # FORMATO TIEMPO
            # =========================
            def fmt(x):
                if pd.isna(x):
                    return "0h 0m"
                h = int(x // 60)
                m = int(x % 60)
                return f"{h}h {m}m"

            df_dep["Promedio_txt"] = df_dep["Promedio"].apply(fmt)

            # =========================
            # GRÁFICO
            # =========================
            fig = px.bar(
                df_dep,
                x="Department",
                y="Promedio",
                text="Promedio_txt",
                title="Tiempo de espera promedio por Departamento"
            )

            fig.update_traces(
                textposition="outside",
                textfont=dict(size=11)
            )

            fig.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                height=550,
                xaxis_tickangle=-30,
                xaxis_title="Departamento",
                yaxis_title="Tiempo de Espera"
            )

            # =========================
            # KPIs
            # =========================
            promedio_global = df_t["Wait_real"].mean()
            p90_global = df_t["Wait_real"].quantile(0.9)
            sla_global = (df_t["Wait_real"] <= 60).mean() * 100

            top = df_dep.iloc[0]
            low = df_dep.iloc[-1]

            # =========================
            # INSIGHTS AUTOMÁTICOS
            # =========================
            insights = html.Div([

                html.H5("Insights automáticos"),

                html.P(
                    f"El departamento con mayor tiempo de espera es '{top['Department']}' con {fmt(top['Promedio'])}."
                ),
                html.P(
                    f"El menor tiempo de espera se observa en '{low['Department']}' con {fmt(low['Promedio'])}."
                ),
                html.P(
                    f"El tiempo promedio general de espera es {fmt(promedio_global)}."
                ),
                html.P(
                    f"El percentil 90 alcanza {fmt(p90_global)}, indicando que un grupo de pacientes experimenta tiempos elevados."
                ),
                html.P(
                    f"El {sla_global:.1f}% de los pacientes es atendido dentro de 60 minutos."
                ),
                html.P(
                    "Existen diferencias entre departamentos que pueden reflejar saturación operativa o cuellos de botella en la atención."
                ),
                html.P(
                    "Se recomienda optimizar los procesos en los departamentos con mayor tiempo de espera."
                )

            ], style={
                "backgroundColor": "#f8f9fa",
                "padding": "15px",
                "borderRadius": "10px"
            })

            # =========================
            # LAYOUT FINAL
            # =========================
            return dbc.Row([

                dbc.Col(dcc.Graph(figure=fig), width=8),

                dbc.Col([
                    insights
                ], width=4)

            ]), k1, k2, k3

        except Exception as e:
            return html.Div(f"Error en TAB 1: {str(e)}"), k1, k2, k3

    # =========================
    # TAB 2 INGRESOS
    # =========================
    if tab == "tab2":

        # usar dataset ORIGINAL sin filtros
        df_ing = df_original.copy()

        # limpiar texto
        df_ing["Admit Type"] = (
            df_ing["Admit Type"]
            .astype(str)
            .str.strip()
            .replace("nan", "No definido")
        )

        # =========================
        # CONTEO REAL
        # =========================
        df_count = (
            df_ing.groupby("Admit Type")
            .size()
            .reset_index(name="Total")
            .sort_values("Total", ascending=False)
        )

        total = df_count["Total"].sum()
        df_count["Porcentaje"] = (df_count["Total"] / total) * 100

        # =========================
        # GRÁFICO
        # =========================
        fig = px.bar(
            df_count,
            x="Admit Type",
            y="Total",
            text=df_count["Total"].apply(lambda x: f"{x:,}"),
            title="Tipos de Ingreso"
        )

        fig.update_traces(textposition="outside")

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            title_x=0.5,
            height=600,
            xaxis_title="Tipo de ingreso",
            yaxis_title="Número de atenciones",
            xaxis_tickangle=-45,
            margin=dict(l=60, r=20, t=60, b=120)
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS 
        # =========================
        top = df_count.iloc[0]
        low = df_count.iloc[-1]

        insights = html.Div([

            html.H5("Insights automáticos"),

            html.P(
                f"El tipo de ingreso más frecuente es '{top['Admit Type']}' con {int(top['Total'])} atenciones ({top['Porcentaje']:.1f}%)."
            ),
            html.P(
                f"El tipo menos frecuente es '{low['Admit Type']}' con {int(low['Total'])} atenciones ({low['Porcentaje']:.1f}%)."
            ),
            html.P(
                f"Total de atenciones analizadas: {int(total)}."
            ),
            html.P(
                "Se observa concentración en ciertos tipos de ingreso, lo que puede indicar dependencia operativa."
            ),

        ], style={
            "backgroundColor": "#f8f9fa",
            "padding": "15px",
            "borderRadius": "10px"
        })

        # =========================
        # LAYOUT
        # =========================
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3
    
    # =========================
    # TAB 3 CALIDAD
    # =========================
    
    if tab == "tab3":

            # DATASET ORIGINAL
            df_cal = df_original.copy()

            # =========================
            # LIMPIEZA
            # =========================
            df_cal = df_cal[["Department", "Care Score"]].dropna()

            # =========================
            # CÁLCULO CORRECTO
            # =========================
            df_cal = (
                df_cal
                .groupby("Department", as_index=False)
                .agg(
                    total_score=("Care Score", "sum"),
                    total_atenciones=("Care Score", "count")
                )
            )

            df_cal["Care Score"] = df_cal["total_score"] / df_cal["total_atenciones"]

            # =========================
            # ORDEN
            # =========================
            df_cal = df_cal.sort_values("Care Score", ascending=False)

            # =========================
            # CLASIFICACIÓN
            # =========================
            def nivel(x):
                if x <= 4:
                    return "Baja"
                elif x <= 7:
                    return "Media"
                else:
                    return "Alta"

            df_cal["Nivel"] = df_cal["Care Score"].apply(nivel)

            # =========================
            # GRÁFICO
            # =========================
            fig = px.bar(
                df_cal,
                x="Department",
                y="Care Score",
                text=df_cal["Care Score"].round(2),
                color="Nivel",
                color_discrete_map={
                    "Baja": "#dc3545",
                    "Media": "#ffc107",
                    "Alta": "#198754"
                },
                title="Calificación Promedio por Departamento"
            )

            fig.update_traces(textposition="outside")

            fig.update_layout(
                xaxis_tickangle=-45,
                height=650
            )

            # =========================
            # INSIGHTS
            # =========================
            max_row = df_cal.iloc[0]
            min_row = df_cal.iloc[-1]
            promedio = df_cal["Care Score"].mean()

            # estado
            if promedio <= 4:
                estado = "CRÍTICO"
                color_estado = "#dc3545"
                icono = "🔴"
            elif promedio <= 7:
                estado = "MEDIO"
                color_estado = "#ffc107"
                icono = "🟡"
            else:
                estado = "ÓPTIMO"
                color_estado = "#198754"
                icono = "🟢"

            banner = html.Div(
                f"ESTADO DEL SISTEMA: {estado}",
                style={
                    "backgroundColor": color_estado,
                    "color": "white",
                    "padding": "15px",
                    "textAlign": "center",
                    "fontWeight": "bold",
                    "fontSize": "22px",
                    "borderRadius": "10px",
                    "marginBottom": "15px"
                }
            )

            insights = html.Div([

                html.H5("Insights automáticos"),

                html.P("🔴 Baja (1–4)"),
                html.P("🟡 Media (5–7)"),
                html.P("🟢 Alta (8–10)"),

                html.Br(),

                html.P(f"Calificación más alta: {max_row['Department']} ({max_row['Care Score']:.2f})"),
                html.P(f"Calificación más baja: {min_row['Department']} ({min_row['Care Score']:.2f})"),
                html.P(f"Promedio general: {promedio:.2f}"),

                html.Br(),

                html.P(f"{icono} El sistema presenta un nivel {estado} de calidad.")

            ])

            return html.Div([
                banner,
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=fig), width=8),
                    dbc.Col(insights, width=4)
                ])
            ]), k1, k2, k3


    # TAB 4 TOP 10 DIAGNOSTICOS
    # =========================
    if tab == "tab4":

        df_diag = dff.copy()

        # =========================
        # LIMPIEZA SIN PERDER DATOS
        # =========================
        df_diag["Diagnosis Primary"] = df_diag["Diagnosis Primary"].fillna("No definido")
        df_diag["Department"] = df_diag["Department"].fillna("No definido")

        # =========================
        # TOP 10 DIAGNÓSTICOS
        # =========================
        top_diag = (
            df_diag["Diagnosis Primary"]
            .value_counts()
            .head(10)
            .index
        )

        df_diag = df_diag[df_diag["Diagnosis Primary"].isin(top_diag)]

        # =========================
        # TABLA CRUZADA
        # =========================
        tabla = pd.crosstab(
            df_diag["Diagnosis Primary"],
            df_diag["Department"]
        )

        # =========================
        # % POR DEPARTAMENTO
        # =========================
        tabla_pct = tabla.div(tabla.sum(axis=0), axis=1) * 100

        # =========================
        # HEATMAP
        # =========================
        fig = px.imshow(
            tabla_pct.round(1),
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues",
            title="Top 10 diagnósticos (% por Departamento)"
        )

        fig.update_layout(
            xaxis_title="Departamento",
            yaxis_title="Diagnóstico",
            height=600
        )

        # =========================
        # INSIGHTS
        # =========================
        insights_list = []

        for col in tabla_pct.columns:

            col_data = tabla_pct[col]

            if col_data.sum() == 0:
                continue

            top_d = col_data.idxmax()
            top_v = col_data.max()

            insights_list.append(
                html.P(
                    f"En {col}, el diagnóstico más frecuente es '{top_d}' con {top_v:.1f}%."
                )
            )

        insights = html.Div(
            [html.H5("Insights automáticos")] + insights_list,
            style={
                "backgroundColor": "#f8f9fa",
                "padding": "15px",
                "borderRadius": "10px"
            }
        )

        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3



    # =========================
    # TAB 5 VOLUMEN MENSUAL
    # =========================
    
    if tab == "tab5":

        df_vol = dff.copy()

        # =========================
        # FECHA (CHECK-IN)
        # =========================
        df_vol["Check-In Time"] = pd.to_datetime(
            df_vol["Check-In Time"], errors="coerce"
        )

        # =========================
        # AGRUPACIÓN MENSUAL
        # =========================
        df_vol["Mes"] = df_vol["Check-In Time"].dt.to_period("M").astype(str)

        df_mensual = (
            df_vol
            .groupby("Mes")
            .size()
            .reset_index(name="Atenciones")
            .sort_values("Mes")
        )

        # =========================
        # GRÁFICO (LÍNEA + ETIQUETAS)
        # =========================
        fig = px.line(
            df_mensual,
            x="Mes",
            y="Atenciones",
            markers=True,
            title="Tendencia Mensual de Atenciones"
        )

        fig.update_traces(
            mode="lines+markers+text",
            text=[f"{v:,}" for v in df_mensual["Atenciones"]],
            textposition="top center",
            line=dict(width=4, color="#2563eb"),
            marker=dict(size=10, color="#2563eb")
        )

        # =========================
        # EJE Y PERSONALIZADO
        # =========================
        y_max = df_mensual["Atenciones"].max()

        fig.update_yaxes(
            range=[2200, y_max + 50],  # no corta el valor máximo
            tick0=2200,
            dtick=200
        )

        # =========================
        # ESTILO
        # =========================
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=500,
            xaxis_title="Mes",
            yaxis_title="Número de atenciones",
            title_x=0.5,
            margin=dict(t=60, b=60),
            yaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
            xaxis=dict(showgrid=False)
        )

        # =========================
        # INSIGHTS
        # =========================
        max_row = df_mensual.loc[df_mensual["Atenciones"].idxmax()]
        min_row = df_mensual.loc[df_mensual["Atenciones"].idxmin()]
        promedio = df_mensual["Atenciones"].mean()

        insights = html.Div([

            html.H5("Insights automáticos"),

            html.P(
                f"El mes con mayor volumen fue {max_row['Mes']} con {int(max_row['Atenciones'])} atenciones."
            ),
            html.P(
                f"El mes con menor volumen fue {min_row['Mes']} con {int(min_row['Atenciones'])} atenciones."
            ),
            html.P(
                f"El promedio mensual es {promedio:.0f} atenciones."
            ),
            html.P(
                "Se observa una tendencia variable durante el año, con picos en marzo y octubre, y una caída marcada hacia fin de año."
            )

        ], style={
            "backgroundColor": "#f8f9fa",
            "padding": "15px",
            "borderRadius": "10px"
        })

        # =========================
        # LAYOUT FINAL
        # =========================
        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3

if __name__ == "__main__":
    print("CALLBACK EJECUTADO")
    app.run(debug=True, port=8050)
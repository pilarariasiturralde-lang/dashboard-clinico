import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd
import plotly.express as px

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LUX])
server = app.server

# =========================
# DATA
# =========================
df = pd.read_csv("clinical_analytics.csv.gz", compression="gzip")

df["Appt Start Time"] = pd.to_datetime(df["Appt Start Time"], errors="coerce")
df["Check-In Time"] = pd.to_datetime(df["Check-In Time"], errors="coerce")

df["Wait_real"] = (df["Appt Start Time"] - df["Check-In Time"]).dt.total_seconds() / 60
df = df[(df["Wait_real"].notna()) & (df["Wait_real"] >= 0)]

df["Department"] = df["Department"].fillna("Unknown")
df["Encounter Status"] = df["Encounter Status"].fillna("Unknown")
df["Diagnosis Primary"] = df["Diagnosis Primary"].fillna("Unknown")

# =========================
# KPI COMPACTO
# =========================
def kpi(title, value, color, extra):
    return dbc.Card(
        dbc.CardBody([
            html.P(title.upper(), style={"fontSize": "11px", "color": "#6c757d"}),
            html.H3(value, style={"marginBottom": "2px"}),
            html.Small(extra, style={"color": color})
        ]),
        style={
            "borderRadius": "10px",
            "padding": "10px",
            "boxShadow": "0 1px 4px rgba(0,0,0,0.06)",
            "height": "110px"
        }
    )

# =========================
# LAYOUT
# =========================
app.layout = dbc.Container([

    html.H2("Dashboard Clínico"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(df["Department"].unique(), multi=True, placeholder="Departamento", id="dep")),
        dbc.Col(dcc.Dropdown(df["Encounter Status"].unique(), multi=True, placeholder="Estado", id="status")),
        dbc.Col(dcc.DatePickerRange(
            start_date=df["Appt Start Time"].min(),
            end_date=df["Appt Start Time"].max(),
            id="fecha"
        ))
    ], className="mb-3"),

    dbc.Row([
        dbc.Col(html.Div(id="kpi1"), width=4),
        dbc.Col(html.Div(id="kpi2"), width=4),
        dbc.Col(html.Div(id="kpi3"), width=4),
    ], className="mb-3"),

    dbc.Tabs([
        dbc.Tab(label="⏱ Tiempos", tab_id="tab1"),
        dbc.Tab(label="📊 Ingresos", tab_id="tab2"),
        dbc.Tab(label="⭐ Calidad", tab_id="tab3"),
        dbc.Tab(label="🧠 Diagnósticos", tab_id="tab4"),
        dbc.Tab(label="📈 Volumen", tab_id="tab5"),
    ], id="tabs", active_tab="tab1"),

    html.Div(id="contenido")

], fluid=True, style={"backgroundColor": "#f5f7fa"})

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

    dff = df

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

    promedio = dff["Wait_real"].mean()
    sla = (dff["Wait_real"] <= 60).mean() * 100
    total = len(dff)

    def fmt(x):
        return f"{int(x//60)}h {int(x%60)}m"

    k1 = kpi("Tiempo espera", fmt(promedio), "#198754", "Normal")
    k2 = kpi("Total", f"{total:,}", "#198754", "Global")
    k3 = kpi("Pacientes atendidos ≤ 60 min", f"{sla:.1f}%", "#ffc107", "Mejorable")

    # =========================
    # TAB 1 TIEMPOS
    # =========================
    if tab == "tab1":

        # AGRUPACIÓN
        df_dep = dff.groupby("Department")["Wait_real"].mean().reset_index()
        df_dep = df_dep.sort_values("Wait_real", ascending=False)

        # FORMATO TIEMPO
        def fmt(x):
            return f"{int(x//60)}h {int(x%60)}m"

        df_dep["label"] = df_dep["Wait_real"].apply(fmt)

        # =========================
        # GRÁFICO
        # =========================
        fig = px.bar(
            df_dep,
            x="Department",
            y="Wait_real",
            text="label"
        )

        # 🔥 CLAVE: mostrar etiquetas correctamente
        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=11, color="black")
        )

        # 🔥 CLAVE REAL: dar espacio arriba
        max_y = df_dep["Wait_real"].max()

        fig.update_layout(
            title="Tiempo de espera promedio por Departamento",
            xaxis_title="Departamento",
            yaxis_title="Tiempo de Espera",
            yaxis=dict(range=[0, max_y * 1.25]),  # 👈 SOLUCIÓN
            margin=dict(t=100)
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS PRO
        # =========================
        top = df_dep.iloc[0]
        low = df_dep.iloc[-1]

        promedio = dff["Wait_real"].mean()
        p90 = dff["Wait_real"].quantile(0.90)
        sla = (dff["Wait_real"] <= 60).mean() * 100

        insights = html.Div([
            html.H5("INSIGHTS AUTOMÁTICOS"),

            html.P(f"El departamento con mayor tiempo de espera es '{top['Department']}' con {fmt(top['Wait_real'])}."),

            html.P(f"El menor tiempo de espera se observa en '{low['Department']}' con {fmt(low['Wait_real'])}."),

            html.P(f"El tiempo promedio general de espera es {fmt(promedio)}."),

            html.P(f"El percentil 90 alcanza {fmt(p90)}, indicando que un grupo de pacientes experimenta tiempos elevados."),

            html.P(f"El {sla:.1f}% de los pacientes es atendido dentro de 60 minutos."),

            html.P("Existen diferencias entre departamentos que pueden reflejar saturación operativa o cuellos de botella en la atención."),

            html.P("Se recomienda optimizar los procesos en los departamentos con mayor tiempo de espera.")
        ])

        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3

    # =========================
    # TAB 2 INGRESOS
    # =========================
    if tab == "tab2":

        # AGRUPACIÓN
        df_count = dff["Admit Type"].value_counts().reset_index()
        df_count.columns = ["Admit Type", "count"]

        total_ing = df_count["count"].sum()

        # porcentaje
        df_count["perc"] = (df_count["count"] / total_ing * 100).round(1)

        # etiquetas
        df_count["label"] = df_count["count"].apply(lambda x: f"{x:,}")

        # GRÁFICO
        fig = px.bar(
            df_count,
            x="Admit Type",
            y="count",
            text="label"
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False   # 🔑 evita que se corten
        )

        fig.update_layout(
            title="Tipos de Ingreso",
            xaxis_title="Tipo de ingreso",
            yaxis_title="Número de atenciones"
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS
        # =========================
        top = df_count.iloc[0]
        low = df_count.iloc[-1]

        insights = html.Div([
            html.H5("INSIGHTS AUTOMÁTICOS"),

            html.P(
                f"El tipo de ingreso más frecuente es '{top['Admit Type']}' "
                f"con {top['count']:,} atenciones ({top['perc']}%)."
            ),

            html.P(
                f"El tipo menos frecuente es '{low['Admit Type']}' "
                f"con {low['count']:,} atenciones ({low['perc']}%)."
            ),

            html.P(f"Total de atenciones analizadas: {total_ing:,}."),

            html.P(
                "Se observa concentración en ciertos tipos de ingreso, lo que puede indicar dependencia operativa."
            )
        ])

        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3
    # =========================
    # TAB 3 CALIDAD
    # =========================
    if tab == "tab3":

        # AGRUPACIÓN
        df_cal = dff.groupby("Department")["Care Score"].mean().reset_index()
        df_cal = df_cal.sort_values("Care Score", ascending=False)

        # etiquetas
        df_cal["label"] = df_cal["Care Score"].round(2)

        # niveles
        def nivel(x):
            if x < 5:
                return "Baja"
            elif x < 7:
                return "Media"
            else:
                return "Alta"

        df_cal["Nivel"] = df_cal["Care Score"].apply(nivel)

        color_map = {
            "Baja": "#dc3545",
            "Media": "#ffc107",
            "Alta": "#198754"
        }

        # GRÁFICO
        fig = px.bar(
            df_cal,
            x="Department",
            y="Care Score",
            text="label",
            color="Nivel",
            color_discrete_map=color_map
        )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            title="Calificación Promedio por Departamento",
            xaxis_title="Departamento",
            yaxis_title="Care Score"
        )

        # =========================
        # ESTADO DEL SISTEMA
        # =========================
        promedio = df_cal["Care Score"].mean()

        if promedio < 5:
            estado = "CRÍTICO"
            color_estado = "#dc3545"
        elif promedio < 7:
            estado = "MEDIO"
            color_estado = "#ffc107"
        else:
            estado = "ÓPTIMO"
            color_estado = "#198754"

        banner = html.Div(
            f"ESTADO DEL SISTEMA: {estado}",
            style={
                "background": color_estado,
                "color": "white",
                "padding": "10px",
                "textAlign": "center",
                "fontWeight": "bold",
                "marginBottom": "10px",
                "borderRadius": "6px"
            }
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS
        # =========================
        max_row = df_cal.iloc[0]
        min_row = df_cal.iloc[-1]

        insights = html.Div([
            html.H5("INSIGHTS AUTOMÁTICOS"),

            html.P("🔴 Baja (1–4)"),
            html.P("🟡 Media (5–7)"),
            html.P("🟢 Alta (8–10)"),

            html.Br(),

            html.P(f"Calificación más alta: {max_row['Department']} ({max_row['Care Score']:.2f})"),
            html.P(f"Calificación más baja: {min_row['Department']} ({min_row['Care Score']:.2f})"),
            html.P(f"Promedio general: {promedio:.2f}"),

            html.Br(),

            html.P(f"🔴 El sistema presenta un nivel {estado} de calidad.")
        ])

        return html.Div([
            banner,
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig), width=8),
                dbc.Col(insights, width=4)
            ])
        ]), k1, k2, k3

    # =========================
    # TAB 4 DIAGNÓSTICOS
    # =========================
    if tab == "tab4":

        # TOP 10 diagnósticos
        top_diag = dff["Diagnosis Primary"].value_counts().head(10).index

        df_diag = dff[
            (dff["Diagnosis Primary"].isin(top_diag)) &
            (dff["Diagnosis Primary"] != "Unknown")
        ]

        # TABLA %
        tabla = pd.crosstab(
            df_diag["Diagnosis Primary"],
            df_diag["Department"],
            normalize="columns"
        ) * 100

        tabla = tabla.round(1)

        # ORDENAR
        tabla = tabla.loc[tabla.sum(axis=1).sort_values(ascending=False).index]

        # 🔥 QUITAR CEROS (CLAVE)
        tabla_visual = tabla.copy()
        tabla_visual[tabla_visual < 1] = None   # 👈 elimina ruido

        # HEATMAP
        fig = px.imshow(
            tabla_visual,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues"
        )

        fig.update_layout(
            title="Top 10 diagnósticos (% por Departamento)",
            xaxis_title="Departamento",
            yaxis_title="Diagnóstico"
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS PRO
        # =========================
        insights_list = []

        for col in tabla.columns:
            if tabla[col].sum() == 0:
                continue

            top_diag_dep = tabla[col].idxmax()
            val = tabla[col].max()

            insights_list.append(
                html.P(
                    f"En {col}, el diagnóstico más frecuente es '{top_diag_dep}' con {val:.1f}%."
                )
            )

        insights = html.Div([
            html.H5("INSIGHTS AUTOMÁTICOS"),
            *insights_list
        ])

        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3

    # =========================
    # TAB 5 VOLUMEN
    # =========================
    if tab == "tab5":

        # crear mes sin romper memoria
        df_temp = dff.assign(
            Mes=dff["Check-In Time"].dt.to_period("M").astype(str)
        )

        df_m = df_temp.groupby("Mes").size().reset_index(name="Atenciones")

        # ordenar correctamente por fecha
        df_m["Mes_dt"] = pd.to_datetime(df_m["Mes"])
        df_m = df_m.sort_values("Mes_dt")

        # etiquetas
        df_m["label"] = df_m["Atenciones"].apply(lambda x: f"{x:,}")

        # GRÁFICO
        fig = px.line(
            df_m,
            x="Mes",
            y="Atenciones",
            markers=True,
            text="label"
        )

        fig.update_traces(
            textposition="top center"
        )

        fig.update_layout(
            title="Tendencia Mensual de Atenciones",
            xaxis_title="Mes",
            yaxis_title="Número de atenciones"
        )

        # =========================
        # INSIGHTS AUTOMÁTICOS PRO
        # =========================
        max_row = df_m.iloc[df_m["Atenciones"].idxmax()]
        min_row = df_m.iloc[df_m["Atenciones"].idxmin()]
        promedio = df_m["Atenciones"].mean()

        insights = html.Div([
            html.H5("INSIGHTS AUTOMÁTICOS"),

            html.P(
                f"El mes con mayor volumen fue {max_row['Mes']} con {max_row['Atenciones']:,} atenciones."
            ),

            html.P(
                f"El mes con menor volumen fue {min_row['Mes']} con {min_row['Atenciones']:,} atenciones."
            ),

            html.P(
                f"El promedio mensual es {int(promedio)} atenciones."
            ),

            html.P(
                "Se observa una tendencia variable durante el año, con picos en algunos meses y una caída marcada hacia fin de año."
            )
        ])

        return dbc.Row([
            dbc.Col(dcc.Graph(figure=fig), width=8),
            dbc.Col(insights, width=4)
        ]), k1, k2, k3

if __name__ == "__main__":
    print("EJECUTADO")
    app.run(debug=True)

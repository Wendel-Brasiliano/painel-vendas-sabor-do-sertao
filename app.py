import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Sabor do Sertão", layout="wide")
st.title("Painel de Vendas: Sabor do Sertão")

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


@st.cache_data
def carregar(arquivo):
    return pd.read_csv(arquivo, parse_dates=["data"])


arquivo = st.sidebar.file_uploader("Envie o CSV de vendas", type=["csv"])
if arquivo is None:
    st.info("Envie o arquivo para começar.")
    st.stop()

df = carregar(arquivo)

# ---------------------------------------------------------------- Nível 1
st.header("1. Exploração dos dados")
st.subheader("Primeiras linhas")
st.dataframe(df.head(10), width="stretch")

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Resumo estatístico")
    st.dataframe(df.describe(include="number"), width="stretch")
with col_b:
    st.subheader("Valores ausentes por coluna")
    st.dataframe(df.isna().sum().rename("ausentes"), width="stretch")

# Tratamento: preencher avaliacao ausente com a mediana
mediana_aval = df["avaliacao"].median()
df["avaliacao"] = df["avaliacao"].fillna(mediana_aval)
st.caption(
    f"Tratamento: os ausentes de 'avaliacao' foram preenchidos com a mediana ({mediana_aval:.0f}). "
    "A nota é uma escala discreta de 1 a 5, então a mediana mantém um valor válido da escala "
    "e é robusta a extremos. Remover as linhas descartaria vendas reais e distorceria o "
    "faturamento, e são poucos casos (cerca de 1% das linhas)."
)

# Colunas auxiliares
df["mes"] = df["data"].dt.to_period("M").astype(str)
df["dia_semana"] = df["data"].dt.dayofweek.map(dict(enumerate(DIAS)))

# ---------------------------------------------------------------- Nível 3
st.sidebar.header("Filtros")
cidades = st.sidebar.multiselect(
    "Cidade", sorted(df["cidade"].unique()), default=sorted(df["cidade"].unique())
)
categorias = st.sidebar.multiselect(
    "Categoria", sorted(df["categoria"].unique()), default=sorted(df["categoria"].unique())
)
dmin, dmax = df["data"].min().date(), df["data"].max().date()
periodo = st.sidebar.date_input("Período", value=(dmin, dmax), min_value=dmin, max_value=dmax)

if isinstance(periodo, (tuple, list)):
    inicio = periodo[0]
    fim = periodo[1] if len(periodo) > 1 else periodo[0]
else:
    inicio = fim = periodo

filtrado = df[
    df["cidade"].isin(cidades)
    & df["categoria"].isin(categorias)
    & (df["data"].dt.date >= inicio)
    & (df["data"].dt.date <= fim)
]

if filtrado.empty:
    st.warning("Nenhuma venda para os filtros selecionados.")
    st.stop()

# ---------------------------------------------------------------- Nível 2
st.header("2. Indicadores")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Faturamento total", f"R$ {filtrado['total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
k2.metric("Número de vendas", f"{len(filtrado):,}".replace(",", "."))
k3.metric("Ticket médio", f"R$ {filtrado['total'].mean():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
k4.metric("Avaliação média", f"{filtrado['avaliacao'].mean():.2f} ⭐".replace(".", ","))

# ---------------------------------------------------------------- Nível 4
st.header("3. Gráficos")
abas = st.tabs([
    "Faturamento mensal",
    "Por cidade",
    "Top 5 produtos",
    "Formas de pagamento",
    "Mapa de calor",
    "Explorador livre",
])

with abas[0]:
    mensal = filtrado.groupby("mes", as_index=False)["total"].sum()
    fig = px.line(mensal, x="mes", y="total", markers=True,
                  title="Faturamento mensal",
                  labels={"mes": "Mês", "total": "Faturamento (R$)"})
    st.plotly_chart(fig, width="stretch")

with abas[1]:
    por_cidade = (filtrado.groupby("cidade", as_index=False)["total"].sum()
                  .sort_values("total", ascending=False))
    fig = px.bar(por_cidade, x="cidade", y="total", text_auto=".2s",
                 title="Faturamento por cidade",
                 labels={"cidade": "Cidade", "total": "Faturamento (R$)"})
    st.plotly_chart(fig, width="stretch")

with abas[2]:
    top5 = (filtrado.groupby("produto", as_index=False)["quantidade"].sum()
            .nlargest(5, "quantidade").sort_values("quantidade"))
    fig = px.bar(top5, x="quantidade", y="produto", orientation="h", text="quantidade",
                 title="Top 5 produtos mais vendidos (quantidade)",
                 labels={"produto": "Produto", "quantidade": "Unidades vendidas"})
    st.plotly_chart(fig, width="stretch")

with abas[3]:
    pagto = filtrado.groupby("pagamento", as_index=False)["total"].sum()
    fig = px.pie(pagto, names="pagamento", values="total", hole=0.4,
                 title="Participação das formas de pagamento no faturamento")
    st.plotly_chart(fig, width="stretch")

with abas[4]:
    fig = px.density_heatmap(
        filtrado, x="hora", y="dia_semana", z="total", histfunc="sum",
        category_orders={"dia_semana": DIAS},
        title="Faturamento por dia da semana e hora",
        labels={"hora": "Hora do dia", "dia_semana": "Dia da semana", "total": "Faturamento (R$)"},
        color_continuous_scale="YlOrRd",
    )
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- Bônus
with abas[5]:
    st.write("Envie qualquer CSV (ou use os dados filtrados do painel) e monte o gráfico que quiser.")
    outro = st.file_uploader("CSV para explorar (opcional)", type=["csv"], key="livre")
    base = pd.read_csv(outro) if outro is not None else filtrado.drop(columns=["mes", "dia_semana"])

    colunas = list(base.columns)
    c1, c2, c3, c4 = st.columns(4)
    eixo_x = c1.selectbox("Eixo X", colunas, key="x")
    eixo_y = c2.selectbox("Eixo Y", colunas, index=min(1, len(colunas) - 1), key="y")
    tipo = c3.selectbox("Tipo de gráfico", ["Dispersão", "Linha", "Barras", "Histograma", "Box plot"], key="tipo")
    agregacao = c4.selectbox("Agregação do Y", ["Nenhuma", "Soma", "Média", "Contagem"], key="agg")

    dados = base
    if agregacao != "Nenhuma" and tipo in ("Linha", "Barras"):
        func = {"Soma": "sum", "Média": "mean", "Contagem": "count"}[agregacao]
        try:
            dados = base.groupby(eixo_x, as_index=False)[eixo_y].agg(func)
        except Exception:
            st.warning("Não foi possível agregar essa combinação de colunas.")

    try:
        if tipo == "Dispersão":
            fig = px.scatter(dados, x=eixo_x, y=eixo_y)
        elif tipo == "Linha":
            fig = px.line(dados.sort_values(eixo_x), x=eixo_x, y=eixo_y)
        elif tipo == "Barras":
            fig = px.bar(dados, x=eixo_x, y=eixo_y)
        elif tipo == "Histograma":
            fig = px.histogram(dados, x=eixo_x)
        else:
            fig = px.box(dados, x=eixo_x, y=eixo_y)
        fig.update_layout(title=f"{tipo}: {eixo_y} por {eixo_x}")
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Não foi possível montar esse gráfico: {e}")

# ---------------------------------------------------------------- Nível 5
st.header("4. Insights para o gestor")

cidade_top = filtrado.groupby("cidade")["total"].sum().idxmax()
fat_cidade = filtrado.groupby("cidade")["total"].sum().max()
part_cidade = fat_cidade / filtrado["total"].sum() * 100

hora_pico = filtrado[filtrado["cidade"] == cidade_top].groupby("hora")["total"].sum().idxmax()
dia_pico = filtrado.groupby("dia_semana")["total"].sum().idxmax()

cat_top = filtrado.groupby("categoria")["total"].sum().idxmax()
part_cat = filtrado.groupby("categoria")["total"].sum().max() / filtrado["total"].sum() * 100

pg = filtrado.groupby("pagamento")["total"].sum()
pg_top = pg.idxmax()
part_pg = pg.max() / pg.sum() * 100

st.markdown(f"""
1. **Onde vender:** {cidade_top} lidera o faturamento, com {part_cidade:.1f}% do total. O horário de pico nessa cidade é às **{hora_pico}h**, e o dia mais forte da rede é **{dia_pico.lower()}**.
2. **O que vender:** a categoria **{cat_top}** é a que mais fatura ({part_cat:.1f}% do total), o que indica onde concentrar estoque e promoções.
3. **Como pagam:** **{pg_top}** é a forma de pagamento mais usada ({part_pg:.1f}% do faturamento). Vale priorizar maquininhas e QR Code estáveis nessa modalidade.
""")

st.download_button(
    "Baixar CSV filtrado",
    data=filtrado.drop(columns=["mes", "dia_semana"]).to_csv(index=False).encode("utf-8"),
    file_name="vendas_filtradas.csv",
    mime="text/csv",
)

import os
import glob
import gc
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Otimizações de performance
gc.enable()
pd.options.mode.copy_on_write = True


st.set_page_config(
    page_title="Desempenho de Campanhas de Discagem",
    layout="wide",
)


ROOT_DIR = "."  # raiz do workspace (pasta Ocorrências)


@st.cache_data
def carregar_csv(path: str) -> pd.DataFrame:
    """
    Lê um CSV de ocorrências em português (como o exemplo de Recadastro)
    e padroniza os nomes das colunas. Otimizado para performance.
    """
    # primeiro tenta UTF-8 (onde os acentos ficam corretos),
    # depois faz fallback para latin1 se der erro
    try:
        df = pd.read_csv(
            path, 
            sep=";", 
            encoding="utf-8-sig",
            dtype={"Número": str, "Mailing": str, "Operador": str, "Status": str},
            na_values=['', '-', 'nan']
        )
    except (UnicodeDecodeError, Exception):
        try:
            df = pd.read_csv(
                path, 
                sep=";", 
                encoding="latin1", 
                errors="ignore",
                dtype={"Número": str, "Mailing": str, "Operador": str, "Status": str},
                na_values=['', '-', 'nan']
            )
        except Exception:
            return pd.DataFrame()  # retorna vazio se falhar

    if df.empty:
        return df

    df.columns = [c.strip() for c in df.columns]

    # inclui variações com problema de acentuação (SubclassificaÃ§Ã£o)
    rename_map = {
        "Número": "numero",
        "Numero": "numero",
        "Mailing": "mailing",
        "Operador": "operador",
        "Texto de Integração": "texto_integracao",
        "Texto de Integracao": "texto_integracao",
        "Finalizado": "finalizado",
        "Status": "status",
        "Classificação": "classificacao",
        "Classificacao": "classificacao",
        "Subclassificação": "subclassificacao",
        "Subclassificacao": "subclassificacao",
        "SubclassificaÃ§Ã£o": "subclassificacao",
        "Data que ligou": "data_ligacao",
        "Data que ligou ": "data_ligacao",
    }

    df = df.rename(columns=rename_map)

    # Converter data/hora (formato: 30/01/2026  09:18:40 ou 30/01/2026 09:18:40)
    if "data_ligacao" in df.columns:
        s = df["data_ligacao"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        df["data_ligacao_datetime"] = pd.to_datetime(
            s, format="%d/%m/%Y %H:%M:%S", dayfirst=True, errors="coerce"
        )
        if df["data_ligacao_datetime"].isna().all():
            df["data_ligacao_datetime"] = pd.to_datetime(s, dayfirst=True, errors="coerce")
        df["data_ligacao_data"] = df["data_ligacao_datetime"].dt.date
        df["hora_ligacao"] = df["data_ligacao_datetime"].dt.hour
        h = df["hora_ligacao"]
        # expediente fixo: 8h às 17h, demais horas marcadas como "Fora do expediente"
        df["faixa_horaria"] = np.select(
            [
                (h >= 8) & (h <= 11),  # manhã
                (h >= 12) & (h <= 17),  # tarde
            ],
            ["Manhã (8-11)", "Tarde (12-17)"],
            default="Fora do expediente",
        )

    # Extrair DDD do número (primeiros 2 dígitos)
    if "numero" in df.columns:
        s = df["numero"].astype(str).str.replace(r"\D", "", regex=True)
        df["ddd"] = s.str[:2]

    return df


@st.cache_data
def carregar_todos_dados() -> pd.DataFrame:
    """
    Varre as pastas que seguem o padrão:
    - ./Ocorrências Prospecção/ANO/MÊS/arquivos.csv
    - ./Ocorrências Recadastro/ANO/MÊS/arquivos.csv
    - ./Ocorrências Repescagem/ANO/MÊS/arquivos.csv
    - ./Ocorrências URA/ANO/MÊS/arquivos.csv

    e consolida em um único dataframe.
    """
    padroes_pasta = [
        os.path.join(ROOT_DIR, "Ocorrências Prospecção", "**", "*.csv"),
        os.path.join(ROOT_DIR, "Ocorrências Recadastro", "**", "*.csv"),
        os.path.join(ROOT_DIR, "Ocorrências Repescagem", "**", "*.csv"),
        os.path.join(ROOT_DIR, "Ocorrências URA", "**", "*.csv"),
    ]

    arquivos = []
    for pattern in padroes_pasta:
        arquivos.extend(glob.glob(pattern, recursive=True))

    # Limitar a 100 arquivos mais recentes para evitar timeout
    if len(arquivos) > 100:
        arquivos = sorted(arquivos, key=os.path.getmtime, reverse=True)[:100]

    dfs = []
    for path in arquivos:
        try:
            df = carregar_csv(path)
            
            # Skip arquivos vazios
            if df.empty or len(df) == 0:
                continue

            # campanha/canal a partir da parte do caminho que começa com "Ocorrências"
            partes = os.path.normpath(path).split(os.sep)
            pasta_campanha = None
            for p in partes:
                if p.startswith("Ocorrências"):
                    pasta_campanha = p
                    break

            # Exemplos de pasta_campanha: "Ocorrências Recadastro", "Ocorrências URA"
            campanha_tipo = (
                pasta_campanha.replace("Ocorrências", "").strip()
                if pasta_campanha
                else "Desconhecida"
            )

            df["campanha"] = campanha_tipo

            # ano / mês a partir do caminho (se existirem)
            ano = None
            mes = None
            for p in partes:
                if p.isdigit() and len(p) == 4:  # ano
                    ano = p
                elif p.lower() in [
                    "janeiro",
                    "fevereiro",
                    "marco",
                    "março",
                    "abril",
                    "maio",
                    "junho",
                    "julho",
                    "agosto",
                    "setembro",
                    "outubro",
                    "novembro",
                    "dezembro",
                ]:
                    mes = p

            df["ano_pasta"] = ano
            df["mes_pasta"] = mes
            df["arquivo_origem"] = os.path.basename(path)

            # usar diretamente a Subclassificação como tabulação principal
            if "subclassificacao" not in df.columns:
                df["subclassificacao"] = np.nan

            df["tabulacao"] = df["subclassificacao"].fillna("")

            dfs.append(df)
        except Exception as e:
            # Log de erro silencioso para não interromper carregamento
            continue

    if not dfs:
        return pd.DataFrame()

    # Usar concat mais rápido com ignore_index
    resultado = pd.concat(dfs, ignore_index=True)
    
    # Liberar memória
    del dfs
    
    return resultado


def preparar_alvo_positivo(dados: pd.DataFrame) -> pd.Series | None:
    """
    Define uma variável binária "positiva" a partir da tabulação
    (coluna subclassificação/tabulacao).
    - Ignora tabulações vazias ou iguais a "-"
    - Usa algumas palavras-chave como positivas
    - Se não encontrar variedade suficiente, faz um fallback:
      considera como positivo tudo que não for "-" nem vazio.
    """
    if "tabulacao" not in dados.columns:
        return None

    t = dados["tabulacao"].astype(str).str.strip()
    # ignora tabulações vazias ou apenas "-"
    t_valid = t[(t != "") & (t != "-")].str.upper()
    if t_valid.empty:
        return None

    positivas = [
        "PRODUTIVA",
        "AGENDADA",
        "AGENDADO",
        "VENDA",
        "CONTRATO",
        "PROMESSA DE ABERTURA - LEAD INDICADO",
        "CONTA ENVIADA PARA ANALISE",
        "CONTA ENVIADA PARA ANÁLISE",
        "RETORNO COM AGENDAMENTO",
    ]

    y = t_valid.apply(lambda x: 1 if any(p in x for p in positivas) else 0)

    # se todas ficaram 0 ou todas 1, faz fallback para "tem tabulação válida ou não"
    if y.nunique() < 2:
        y = t_valid.apply(lambda x: 1 if x not in ("", "-") else 0)
        if y.nunique() < 2:
            return None

    # alinhar com o índice original (preenche com 0 onde não havia tabulação válida)
    y_full = pd.Series(0, index=dados.index)
    y_full.loc[t_valid.index] = y
    return y_full


def treinar_modelo_ia(dados: pd.DataFrame):
    """
    Modelo simples de classificação para estimar probabilidade
    de tabulação "positiva" com base em campanha, DDD, ano/mês, etc.
    """
    y = preparar_alvo_positivo(dados)
    if y is None or y.nunique() < 2:
        return None, None, None

    features_cat = []
    for col in ["campanha", "ddd", "ano_pasta", "mes_pasta"]:
        if col in dados.columns:
            features_cat.append(col)

    if not features_cat:
        return None, None, None

    X = dados[features_cat].astype(str).fillna("")
    X = pd.get_dummies(X, drop_first=True)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    modelo = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
    )
    modelo.fit(X_train, y_train)
    score = modelo.score(X_test, y_test)

    importancias = pd.Series(modelo.feature_importances_, index=X.columns).sort_values(
        ascending=False
    )

    return modelo, score, importancias


def kpi_box(col, titulo, valor, formato="{:,.0f}"):
    col.metric(titulo, formato.format(valor) if pd.notnull(valor) else "-")


def gerar_resumo_automatico(dados_filtrados: pd.DataFrame, y_pos: pd.Series | None, data_inicial, data_final):
    linhas = []
    if data_inicial and data_final:
        if data_inicial == data_final:
            linhas.append(f"- Período analisado: **{data_inicial.strftime('%d/%m/%Y')}**.")
        else:
            linhas.append(
                f"- Período analisado: **{data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')}**."
            )
    total_lig = len(dados_filtrados)
    if total_lig > 0:
        linhas.append(f"- Total de ligações no período e filtros atuais: **{total_lig:,}**.")

    if y_pos is not None and "campanha" in dados_filtrados.columns:
        df_aux = dados_filtrados.copy()
        df_aux["_y"] = y_pos
        taxa_camp = (
            df_aux.groupby("campanha")["_y"]
            .mean()
            .reset_index(name="taxa_positiva")
        )
        if not taxa_camp.empty:
            taxa_camp["taxa_positiva"] = (taxa_camp["taxa_positiva"] * 100).round(1)
            melhor = taxa_camp.sort_values("taxa_positiva", ascending=False).iloc[0]
            linhas.append(
                f"- Campanha com melhor taxa de tabulação positiva: **{melhor['campanha']}** "
                f"({melhor['taxa_positiva']}%)."
            )

    if y_pos is not None and "ddd" in dados_filtrados.columns:
        df_aux2 = dados_filtrados.copy()
        df_aux2["_y"] = y_pos
        taxa_ddd = (
            df_aux2.groupby("ddd")["_y"]
            .mean()
            .reset_index(name="taxa_positiva")
        )
        if not taxa_ddd.empty:
            taxa_ddd["taxa_positiva"] = (taxa_ddd["taxa_positiva"] * 100).round(1)
            melhor_ddd = taxa_ddd.sort_values("taxa_positiva", ascending=False).iloc[0]
            linhas.append(
                f"- DDD com melhor taxa positiva: **{melhor_ddd['ddd']}** "
                f"({melhor_ddd['taxa_positiva']}%)."
            )

    if linhas:
        st.markdown("**Resumo automático do período (IA simples):**")
        st.markdown("\n".join(linhas))
        st.markdown("**Insight:** Use este resumo para comunicar resultados e priorizar campanhas e DDDs com melhor desempenho.")


def main():
    st.title("📞 Desempenho de Campanhas de Discagem")
    
    # Carregar dados com feedback visual
    with st.spinner("⏳ Carregando dados dos CSVs... (Isso pode levar alguns minutos na primeira vez)"):
        dados = carregar_todos_dados()

    if dados.empty:
        st.warning(
            "Nenhum CSV encontrado nas pastas de ocorrências. "
            "Verifique se as pastas 'Ocorrências Prospecção', "
            "'Ocorrências Recadastro', 'Ocorrências Repescagem' e 'Ocorrências URA' "
            "estão dentro desta pasta."
        )
        return

    # Filtros laterais
    st.sidebar.header("Filtros")

    if "data_ligacao_data" in dados.columns:
        datas_validas = dados["data_ligacao_data"].dropna()
        min_date = datas_validas.min()
        max_date = datas_validas.max()
    else:
        min_date = max_date = None

    campanhas = sorted(dados["campanha"].dropna().unique()) if "campanha" in dados.columns else []
    ddds = sorted(dados["ddd"].dropna().unique()) if "ddd" in dados.columns else []

    if min_date is not None and max_date is not None:
        periodo = st.sidebar.date_input(
            "Período (data inicial e final)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(periodo, tuple) and len(periodo) == 2:
            data_inicial, data_final = periodo
        else:
            data_inicial = data_final = periodo
    else:
        data_inicial = data_final = None

    campanhas_sel = st.sidebar.multiselect("Campanhas", campanhas, default=campanhas)
    ddds_sel = st.sidebar.multiselect("DDDs", ddds)

    if st.sidebar.button("🔄 Limpar cache e recarregar dados"):
        st.cache_data.clear()
        st.rerun()

    pagina = st.sidebar.selectbox(
        "Visão",
        ["Campanhas / Desempenho", "Operação (Operadores)"],
        index=0,
    )

    dados_filtrados = dados.copy()
    if data_inicial is not None and data_final is not None and "data_ligacao_data" in dados_filtrados.columns:
        dados_filtrados = dados_filtrados[
            (dados_filtrados["data_ligacao_data"] >= data_inicial)
            & (dados_filtrados["data_ligacao_data"] <= data_final)
        ]
    if campanhas_sel:
        dados_filtrados = dados_filtrados[dados_filtrados["campanha"].isin(campanhas_sel)]
    if ddds_sel and "ddd" in dados_filtrados.columns:
        dados_filtrados = dados_filtrados[dados_filtrados["ddd"].isin(ddds_sel)]

    # Página exclusiva de análise da operação
    if pagina == "Operação (Operadores)":
        st.subheader("Análise da Operação - Operadores")

        if "operador" in dados_filtrados.columns:
            df_ops = dados_filtrados.copy()
            df_ops["tabulacao_norm"] = df_ops["tabulacao"].astype(str).str.strip()

            # considera como não classificado:
            # - vazio
            # - texto específico "Não classificado pelo operador" (com ou sem problema de acentuação)
            nao_class_textos = [
                "NÃO CLASSIFICADO PELO OPERADOR",
                "NAO CLASSIFICADO PELO OPERADOR",
                "NÃ£O CLASSIFICADO PELO OPERADOR",
            ]
            tab_upper = df_ops["tabulacao_norm"].str.upper()
            cond_sem_class = (
                (df_ops["tabulacao_norm"] == "")
                | (tab_upper.isin(nao_class_textos))
            )

            resumo_ops = (
                df_ops.groupby("operador")
                .size()
                .reset_index(name="total_ligacoes")
            )
            sem_class = (
                df_ops[cond_sem_class]
                .groupby("operador")
                .size()
                .reindex(resumo_ops["operador"])
                .fillna(0)
                .reset_index(name="nao_classificadas")
            )

            resumo_ops = resumo_ops.merge(sem_class, on="operador")
            resumo_ops["pct_nao_classificada"] = (
                resumo_ops["nao_classificadas"] / resumo_ops["total_ligacoes"] * 100
            ).round(1)

            # produtividade por operador: % de ligações com tabulação positiva
            y_pos_ops = preparar_alvo_positivo(df_ops)
            if y_pos_ops is not None:
                df_ops["_y_pos"] = y_pos_ops
                prod_ops = (
                    df_ops.groupby("operador")["_y_pos"]
                    .mean()
                    .reset_index(name="pct_produtivas")
                )
                prod_ops["pct_produtivas"] = (prod_ops["pct_produtivas"] * 100).round(1)
                resumo_ops = resumo_ops.merge(prod_ops, on="operador", how="left")

            # Ranking de ofensores
            st.write("**Ranking de ofensores (maior % de ligações não classificadas):**")
            df_rank_ofensores = resumo_ops.sort_values(
                ["pct_nao_classificada", "total_ligacoes"],
                ascending=[False, False],
            ).reset_index(drop=True)
            df_rank_ofensores.insert(0, "Rank", df_rank_ofensores.index + 1)
            st.dataframe(
                df_rank_ofensores[
                    ["Rank", "operador", "total_ligacoes", "nao_classificadas", "pct_nao_classificada", "pct_produtivas"]
                ]
            )

            # Ranking de maior volume
            st.write("**Ranking de quem mais recebe ligações (operadores):**")
            df_rank_volume = resumo_ops.sort_values(
                ["total_ligacoes", "pct_nao_classificada"],
                ascending=[False, True],
            ).reset_index(drop=True)
            df_rank_volume.insert(0, "Rank", df_rank_volume.index + 1)
            st.dataframe(
                df_rank_volume[
                    ["Rank", "operador", "total_ligacoes", "nao_classificadas", "pct_nao_classificada", "pct_produtivas"]
                ]
            )
            st.markdown("**Insight:** Ofensores com alto % de não classificação precisam de reforço em tabulação. "
                "O % produtivas indica conversão por operador — use para coaching e metas individuais.")
        else:
            st.info("A coluna 'Operador' não foi encontrada nos dados filtrados.")

        return

    # KPIs
    st.subheader("Visão Geral (filtros aplicados)")
    col1, col2, col3 = st.columns(3)

    total_ligacoes = len(dados_filtrados)
    kpi_box(col1, "Total de Ligações", total_ligacoes)

    # taxa positiva
    y_pos = preparar_alvo_positivo(dados_filtrados)
    if y_pos is not None and len(y_pos) > 0:
        taxa_pos = 100 * y_pos.mean()
        kpi_box(col2, "Taxa de Tabulação Positiva (%)", taxa_pos, "{:,.1f}")

    # quantidade de tabulações únicas
    if "tabulacao" in dados_filtrados.columns:
        kpi_box(col3, "Tabulações Distintas", dados_filtrados["tabulacao"].nunique())

    st.markdown("**Insight:** Os KPIs acima resumem o volume e a qualidade do discado no período. "
        "Taxa positiva maior indica melhor conversão; muitas tabulações distintas sugerem dispersão de resultados.")

    # Análise por horário
    st.markdown("---")
    st.subheader("Análise por Horário")

    # Garantir hora_ligacao se vier de cache antigo
    if "hora_ligacao" not in dados_filtrados.columns and "data_ligacao" in dados_filtrados.columns:
        s = dados_filtrados["data_ligacao"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        dt = pd.to_datetime(s, format="%d/%m/%Y %H:%M:%S", dayfirst=True, errors="coerce")
        if dt.isna().all():
            dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        dados_filtrados["hora_ligacao"] = dt.dt.hour

    if "hora_ligacao" in dados_filtrados.columns and not dados_filtrados.empty:
        # considerar apenas expediente 8h-17h, sem faixas (hora a hora)
        df_horario = dados_filtrados[
            (dados_filtrados["hora_ligacao"] >= 8) & (dados_filtrados["hora_ligacao"] <= 17)
        ].copy()
        if df_horario.empty:
            st.info("Não há ligações no horário de expediente (8h-17h) para os filtros atuais.")
        else:
            g_hora = (
                df_horario.groupby(["hora_ligacao", "campanha"])
                .size()
                .reset_index(name="qtde")
            )
            g_hora = g_hora.sort_values("hora_ligacao")
            fig_hora = px.bar(
                g_hora,
                x="hora_ligacao",
                y="qtde",
                color="campanha",
                barmode="group",
                title="Volume de ligações por hora (8h-17h) e campanha",
            )
            st.plotly_chart(fig_hora, use_container_width=True)

            if y_pos is not None:
                df_hora = df_horario.copy()
                df_hora["_y"] = y_pos.loc[df_hora.index]
                taxa_hora = (
                    df_hora.groupby("hora_ligacao")["_y"]
                    .mean()
                    .reset_index(name="taxa_positiva")
                )
                taxa_hora["taxa_positiva"] = (taxa_hora["taxa_positiva"] * 100).round(1)
                st.write("**Taxa de tabulação positiva por hora (expediente) (%):**")
                st.dataframe(taxa_hora)

                if not taxa_hora.empty:
                    best_time = taxa_hora.loc[taxa_hora["taxa_positiva"].idxmax()]
                    st.success(
                        f"**Best time to call:** {int(best_time['hora_ligacao'])}h — "
                        f"maior taxa de tabulação positiva ({best_time['taxa_positiva']}%) no expediente para os filtros atuais."
                    )
            st.markdown("**Insight:** O gráfico mostra o volume por hora; a tabela indica em quais horários a conversão é maior. "
                "Priorize o best time para otimizar campanhas e recursos.")
    else:
        st.info(
            "A análise por horário precisa da coluna 'Data que ligou' no formato DD/MM/AAAA HH:MM:SS. "
            "Se os dados existem mas não aparecem, recarregue a página (Ctrl+R) ou limpe o cache do Streamlit."
        )

    # Resumo automático em texto (IA simples)
    st.markdown("---")
    gerar_resumo_automatico(dados_filtrados, y_pos, data_inicial, data_final)

    # Gráfico por campanha / tabulação
    st.markdown("---")
    st.subheader("Distribuição de Tabulações por Campanha")

    # sempre ignorar tabulação "-"
    mask_tabs_validas = (
        ("tabulacao" in dados_filtrados.columns)
        and not dados_filtrados.empty
    )
    if mask_tabs_validas:
        df_tabs = dados_filtrados.copy()
        df_tabs["tabulacao"] = df_tabs["tabulacao"].astype(str).str.strip()
        df_tabs = df_tabs[(df_tabs["tabulacao"] != "") & (df_tabs["tabulacao"] != "-")]
    else:
        df_tabs = pd.DataFrame()

    if (
        not df_tabs.empty
        and "campanha" in df_tabs.columns
        and "tabulacao" in df_tabs.columns
    ):
        g = (
            df_tabs.groupby(["campanha", "tabulacao"])
            .size()
            .reset_index(name="qtde")
        )
        fig = px.bar(
            g,
            x="campanha",
            y="qtde",
            color="tabulacao",
            barmode="stack",
            title="Tabulações por Campanha",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Insight:** Cada barra empilhada mostra como as tabulações se distribuem por campanha. "
            "Campanhas com mais segmentos verdes (positivos) tendem a performar melhor.")
    else:
        st.info("Não há colunas suficientes para montar este gráfico.")

    # Gráfico por DDD
    st.markdown("---")
    st.subheader("Tabulações por DDD")

    if (
        not df_tabs.empty
        and "ddd" in df_tabs.columns
        and "tabulacao" in df_tabs.columns
    ):
        gddd = (
            df_tabs.groupby(["ddd", "tabulacao"])
            .size()
            .reset_index(name="qtde")
        )
        figddd = px.bar(
            gddd,
            x="ddd",
            y="qtde",
            color="tabulacao",
            barmode="stack",
            title="Distribuição de Tabulações por DDD",
        )
        st.plotly_chart(figddd, use_container_width=True)
        st.markdown("**Insight:** DDDs com maior concentração de tabulações positivas merecem prioridade; "
            "os com muitas negativas ou improdutivas podem exigir ajuste de abordagem ou horário.")

    # Heatmap de desempenho por DDD e campanha (taxa positiva)
    st.markdown("---")
    st.subheader("Heatmap de desempenho por DDD e campanha")

    if "ddd" in dados_filtrados.columns and "campanha" in dados_filtrados.columns:
        y_full = preparar_alvo_positivo(dados_filtrados)
        if y_full is not None and y_full.sum() >= 0:
            df_mapa = dados_filtrados.copy()
            df_mapa["_y"] = y_full
            taxa_ddd_camp = (
                df_mapa.groupby(["ddd", "campanha"])["_y"]
                .mean()
                .reset_index(name="taxa_positiva")
            )
            taxa_ddd_camp["taxa_positiva"] = (taxa_ddd_camp["taxa_positiva"] * 100).round(1)
            if not taxa_ddd_camp.empty:
                tabela_heat = taxa_ddd_camp.pivot_table(
                    index="ddd",
                    columns="campanha",
                    values="taxa_positiva",
                    fill_value=0,
                )
                fig_heat = px.imshow(
                    tabela_heat,
                    labels=dict(x="Campanha", y="DDD", color="% positivo"),
                    aspect="auto",
                    color_continuous_scale="Greens",
                )
                st.plotly_chart(fig_heat, use_container_width=True)
                st.markdown("**Insight:** Células mais escuras indicam DDDs com melhor conversão em cada campanha. "
                    "Use para alocar esforço e testar estratégias específicas por região.")

    # Indicadores: maior e menor tabulação por campanha (tabela única)
    st.markdown("---")
    st.subheader("Indicadores de Tabulações (maior/menor volume por campanha)")

    if not df_tabs.empty and "campanha" in df_tabs.columns and "tabulacao" in df_tabs.columns:
        g_camp_tab = (
            df_tabs.groupby(["campanha", "tabulacao"])
            .size()
            .reset_index(name="qtde")
        )

        top_camp = (
            g_camp_tab.sort_values(["campanha", "qtde"], ascending=[True, False])
            .groupby("campanha")
            .head(1)
            .rename(columns={"tabulacao": "maior_tabulacao", "qtde": "qtde_maior"})
        )
        bottom_camp = (
            g_camp_tab.sort_values(["campanha", "qtde"], ascending=[True, True])
            .groupby("campanha")
            .head(1)
            .rename(columns={"tabulacao": "menor_tabulacao", "qtde": "qtde_menor"})
        )
        indicadores_camp = top_camp.merge(
            bottom_camp[["campanha", "menor_tabulacao", "qtde_menor"]],
            on="campanha",
            how="left",
        )
        st.dataframe(indicadores_camp[["campanha", "maior_tabulacao", "qtde_maior", "menor_tabulacao", "qtde_menor"]])
        st.markdown("**Insight:** A maior tabulação por campanha indica o principal resultado; a menor ajuda a identificar "
            "o que menos ocorre. Use para calibrar expectativas e metas.")

        if "ddd" in df_tabs.columns:
            g_ddd_tab = (
                df_tabs.groupby(["ddd", "tabulacao"])
                .size()
                .reset_index(name="qtde")
            )
            top_ddd = (
                g_ddd_tab.sort_values(["ddd", "qtde"], ascending=[True, False])
                .groupby("ddd")
                .head(1)
                .reset_index(drop=True)
            )
            st.write("**Maior tabulação por DDD:**")
            st.dataframe(top_ddd)
            st.markdown("**Insight:** DDDs com a mesma tabulação dominante podem ter perfis similares; "
                "compare com o heatmap para priorizar regiões.")

    # Comparação entre dias
    st.markdown("---")
    st.subheader("Comparação entre Dias e Campanhas")

    if "data_ligacao_data" in dados_filtrados.columns and "campanha" in dados_filtrados.columns:
        gdia = (
            dados_filtrados.groupby(["data_ligacao_data", "campanha"])
            .size()
            .reset_index(name="qtde")
        )
        figdia = px.line(
            gdia,
            x="data_ligacao_data",
            y="qtde",
            color="campanha",
            markers=True,
            title="Total de Ligações por Dia e Campanha (com filtros)",
        )
        st.plotly_chart(figdia, use_container_width=True)
        st.markdown("**Insight:** A evolução ao longo dos dias revela tendências e sazonalidade. "
            "Quedas bruscas ou picos merecem investigação.")

    # Alertas de anomalia de dia (taxa positiva muito fora da média)
    if "data_ligacao_data" in dados_filtrados.columns:
        y_alert = preparar_alvo_positivo(dados_filtrados)
        if y_alert is not None and len(dados_filtrados["data_ligacao_data"].unique()) >= 5:
            df_alert = dados_filtrados.copy()
            df_alert["_y"] = y_alert
            diario = (
                df_alert.groupby("data_ligacao_data")["_y"]
                .mean()
                .reset_index(name="taxa_positiva")
            )
            diario["taxa_positiva"] = diario["taxa_positiva"] * 100
            media = diario["taxa_positiva"].mean()
            desvio = diario["taxa_positiva"].std()
            if desvio > 0:
                limite_baixo = media - 1.5 * desvio
                limite_alto = media + 1.5 * desvio
                anomalias = diario[
                    (diario["taxa_positiva"] < limite_baixo)
                    | (diario["taxa_positiva"] > limite_alto)
                ].copy()
                if not anomalias.empty:
                    st.markdown("**Alertas de anomalia de dia (taxa positiva muito fora da média):**")
                    anomalias["desvio_da_media"] = (anomalias["taxa_positiva"] - media).round(1)
                    st.dataframe(anomalias.sort_values("data_ligacao_data"))
                    st.markdown("**Insight:** Dias com desvio negativo indicam pior desempenho que o esperado; "
                        "desvio positivo sugere dias excepcionais. Investigue causas (feriados, mudanças operacionais, etc.).")

    # Follow ups positivos por DDD (com % sobre discado)
    st.markdown("---")
    st.subheader("DDDs com mais follow ups positivos")

    if not df_tabs.empty and "ddd" in df_tabs.columns:
        df_fu = df_tabs.copy()
        fu_list = [
            "PROMESSA DE ABERTURA - LEAD INDICADO",
            "CONTA ENVIADA PARA ANALISE",
            "CONTA ENVIADA PARA ANÁLISE",
            "RETORNO COM AGENDAMENTO",
        ]
        df_fu["tab_upper"] = df_fu["tabulacao"].astype(str).str.upper()
        fu_upper = [s.upper() for s in fu_list]
        df_fu = df_fu[df_fu["tab_upper"].isin(fu_upper)]

        if not df_fu.empty:
            discado_por_ddd = dados_filtrados.groupby("ddd").size()
            discado_por_camp_ddd = dados_filtrados.groupby(["campanha", "ddd"]).size().reset_index(name="discado")

            g_fu_ddd = (
                df_fu.groupby("ddd")
                .size()
                .reset_index(name="qtde_follow_up")
            )
            g_fu_ddd = g_fu_ddd.merge(
                discado_por_ddd.rename("discado"),
                left_on="ddd",
                right_index=True,
                how="left",
            )
            g_fu_ddd["pct_sobre_discado"] = (g_fu_ddd["qtde_follow_up"] / g_fu_ddd["discado"] * 100).round(1)
            g_fu_ddd = g_fu_ddd.sort_values("qtde_follow_up", ascending=False).reset_index(drop=True)
            g_fu_ddd.insert(0, "Rank", g_fu_ddd.index + 1)
            st.write("**Top DDDs com mais follow ups positivos (% sobre o discado):**")
            st.dataframe(g_fu_ddd[["Rank", "ddd", "qtde_follow_up", "discado", "pct_sobre_discado"]])
            st.markdown("**Insight:** DDDs com maior % de follow ups positivos (Promessa de Abertura, Conta Enviada, Retorno com Agendamento) "
                "são os mais promissores. Priorize retornos e campanhas nessas regiões.")

        else:
            st.info(
                "Nenhuma ocorrência das tabulações de follow up positivo "
                "nos dados filtrados."
            )

    # IA
    st.markdown("---")
    st.subheader("IA: Perfis com Maior Probabilidade de Tabulação Positiva")

    if st.checkbox("Treinar/atualizar modelo de IA"):
        with st.spinner("Treinando modelo..."):
            modelo, score, importancias = treinar_modelo_ia(dados)

        if modelo is None:
            st.info(
                "Não foi possível treinar o modelo com os dados atuais. "
                "Verifique se existe variedade suficiente de tabulações."
            )
        else:
            st.success(f"Modelo treinado. Acurácia (validação): {score*100:.1f}%")

            st.markdown("""
            **O que significa a acurácia?**  
            O modelo foi treinado para prever se uma ligação terá tabulação positiva (ex.: Produtiva, Agendada, Promessa de Abertura, Retorno com Agendamento, etc.). 
            A acurácia indica a % de previsões corretas em dados que o modelo nunca viu. 
            Quanto maior, melhor o modelo generaliza.
            """)

            st.write("**Importância das variáveis (features mais relevantes):**")
            st.bar_chart(importancias.head(15))
            st.markdown("""
            **Por que a importância das variáveis importa?**  
            Cada barra mostra o quanto aquela característica (campanha, DDD, ano, mês) influencia a previsão. 
            Variáveis no topo explicam melhor o desempenho: por exemplo, se "ddd_11" ou "campanha_Prospecção" 
            aparecem em destaque, esses segmentos tendem a ter mais tabulações positivas. Use isso para 
            priorizar horários, operadores ou estratégias em DDDs/campanhas com menor performance.
            """)

            if "ddd" in dados.columns:
                y_full = preparar_alvo_positivo(dados)
                taxa_por_ddd = (
                    dados.assign(_y=y_full)
                    .groupby("ddd")["_y"]
                    .mean()
                    .dropna()
                    .sort_values(ascending=False)
                    * 100
                )
                st.write("**Top DDDs com maior taxa de tabulação positiva (%):**")
                st.dataframe(taxa_por_ddd.round(1))
                st.markdown("""
                **O que esse ranking indica?**  
                Esta tabela mostra a % real de ligações positivas por DDD (considerando todas as tabulações 
                positivas: Produtiva, Agendada, Promessa de Abertura, Retorno com Agendamento, etc.). 
                DDDs no topo convertem melhor; os do final merecem análise para entender barreiras 
                (horário, perfil do público, abordagem) e testar melhorias.
                """)


if __name__ == "__main__":
    main()


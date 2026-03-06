# 📞 Desempenho de Campanhas de Discagem

Aplicação Streamlit para análise e visualização de dados de campanhas de discagem.

## 🚀 Deploy no Streamlit Cloud

### Pré-requisitos
- Conta no [GitHub](https://github.com)
- Conta no [Streamlit Community Cloud](https://streamlit.io/cloud)

### Passos para Deploy

1. **Prepare o repositório Git**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Envie para GitHub**
   - Crie um novo repositório no GitHub
   - Faça push dos arquivos:
   ```bash
   git remote add origin https://github.com/seu-usuario/seu-repo.git
   git branch -M main
   git push -u origin main
   ```

3. **Deploy no Streamlit Cloud**
   - Acesse https://share.streamlit.io
   - Faça login com sua conta GitHub
   - Clique em "New app"
   - Selecione seu repositório
   - Branch: `main`
   - Main file path: `app.py`
   - Clique em "Deploy"

### ✅ Configurações Incluídas

- ✔️ `requirements.txt` - Dependências com versões pinadas
- ✔️ `.streamlit/config.toml` - Configurações do Streamlit otimizadas
- ✔️ `.gitignore` - Arquivos a ignorar no Git

### 📁 Estrutura de Dados

A aplicação espera as seguintes pastas com arquivos CSV:
```
Ocorrências Prospecção/2026/Fevereiro/*.csv
Ocorrências Recadastro/2026/Fevereiro/*.csv
Ocorrências Repescagem/2025/Dezembro/*.csv
Ocorrências URA/Fevereiro/*.csv
```

### 🔧 Particularidades do Streamlit Cloud

- Memória limitada: ~1GB
- Sem estado persistente entre recarregamentos
- Timeout: 1 hora por sessão
- Cache automático com `@st.cache_data`

### 📊 Funcionalidades

- Análise por campanha e DDD
- Heatmap de desempenho
- Ranking de operadores
- Predicção com Machine Learning
- Gráficos interativos com Plotly

### 💡 Dicas

- Use os filtros na barra lateral para análises mais rápidas
- Clique em "Limpar cache" se os dados não atualizarem
- O modelo de IA melhora com mais dados históricos

---

**Versão:** 1.0  
**Última atualização:** Março 2026

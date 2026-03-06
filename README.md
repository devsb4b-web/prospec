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
- ✔️ `runtime.txt` - Python 3.11 (compatível com Streamlit Cloud)
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

### ⚠️ Otimizações para Evitar Timeout

A aplicação foi otimizada para:
- ✅ Carregar apenas os 100 arquivos CSV mais recentes
- ✅ Pular arquivos vazios automaticamente
- ✅ Usar tipos de dados eficientes em memória
- ✅ Feedback visual (spinner) enquanto carrega

**Se ainda tiver problemas de carregamento:**

1. **Primeira execução:** A primeira inicialização pode levar até 5 minutos (Streamlit Cloud precisa compilar tudo)
2. **Recarregar página:** Pressione `R` na página para limpar cache
3. **Aguardar mais:** Streamlit Cloud está processando — não feche a página
4. **Verificar erro:** Abra o Developer Console (F12) e veja se há mensagens de erro no Network

### 📊 Funcionalidades

- Análise por campanha e DDD
- Heatmap de desempenho
- Ranking de operadores
- Predicção com Machine Learning (Random Forest)
- Gráficos interativos com Plotly
- Taxa de tabulação positiva por horário

### 💡 Dicas

- Use os filtros na barra lateral para análises mais rápidas
- Clique em "Limpar cache" se os dados não atualizarem
- O modelo de IA melhora com mais dados históricos

### 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| App carregando eternamente | Aguarde a primeira inicialização, recarregue (R), ou limpe cache |
| Erro de MemoryError | Reduzir quantidade de CSVs (máx 100 mais recentes) |
| Filtros não funcionam | Recarregar página (Ctrl+R) |
| Gráficos vazios | Verificar se há dados nos filtros selecionados |

### 🔐 Segurança

Não armazene dados sensíveis em variáveis públicas. Use `st.secrets` para chaves de API.

---

**Versão:** 1.1  
**Última atualização:** Março 2026  
**Status:** ✅ Otimizado para Streamlit Cloud

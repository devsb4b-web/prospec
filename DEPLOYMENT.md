# DEPLOYMENT CHECKLIST

## ✅ Antes de fazer Deploy no Streamlit Cloud

- [ ] Todos os arquivos CSV estão nas pastas corretas?
- [ ] Executou `git add .` e `git commit -m "message"`?
- [ ] Fez push para GitHub (`git push -u origin main`)?
- [ ] `requirements.txt` está atualizado?
- [ ] `.streamlit/config.toml` existe?
- [ ] `runtime.txt` especifica Python 3.11?

## 🚀 Passo a Passo do Deploy

1. Abra https://share.streamlit.io
2. Clique em "New app"
3. Selecione seu repositório GitHub
4. Confirme:
   - Branch: `main`
   - Main file: `app.py`
5. Clique "Deploy"

## ⏳ Primeira Inicialização

- **Tempo esperado:** 3-5 minutos
- **Por que demora:** Streamlit Cloud compila dependências, pandas é grande
- **Não feche:** Deixe a página aberta até completar

## 🔍 Se Ficar Carregando

1. Pressione Ctrl+R para recarregar
2. Limpe o cache do navegador
3. Abra DevTools (F12) e veja se há erros
4. Aguarde mais 2 minutos

## ✅ Sucesso!

Quando ver "📞 Desempenho de Campanhas de Discagem" na tela, funcionou!

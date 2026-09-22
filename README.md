# Controle Catedral — versão iOS

App de controle remoto do **Holyrics** para iPhone/iPad, empacotado a partir do mesmo HTML5 da versão Android.

## Como funciona

1. Você edita `www/index.html` no GitHub
2. Push pra `main` dispara o build automático
3. GitHub Actions compila num Mac virtual e gera o `.ipa`
4. Você baixa o `.ipa` e instala no iPhone via **Sideloadly** (ferramenta grátis)

## Instalação no iPhone (passo a passo)

### 1. Baixar o IPA
- Vai na aba **Actions** do seu repositório no GitHub
- Clica no último build verde (✅)
- Scrolla até **Artifacts** e baixa `controle-catedral-unsigned`
- Descompacta o ZIP → você vai ter um arquivo `controle-catedral.ipa`

### 2. Instalar o Sideloadly no PC
- Acessa https://sideloadly.io
- Baixa a versão Windows
- Instala normalmente (next, next, finish)

### 3. Instalar o app no iPhone
- Conecta o iPhone/iPad no PC via cabo USB
- Abre o **Sideloadly**
- Arrasta o arquivo `controle-catedral.ipa` pra cima do Sideloadly
- Preenche:
  - **Apple ID**: seu email do iCloud (pode ser o gratuito)
  - **Password**: senha da Apple ID
- Clica em **Start**
- Aguarda ~30 segundos

### 4. Confiar no desenvolvedor (primeira vez só)
- No iPhone: **Ajustes → Geral → Gerenciamento de VPN e Dispositivo**
- Toca no nome do desenvolvedor (seu email)
- Toca em **Confiar** → confirma

### 5. Usar o app
- Abre o app **Controle Catedral** no iPhone
- Primeira vez: aparece popup perguntando permissão de **Rede Local** → toque em **OK**
- Pronto, vai conectar no Holyrics automaticamente

⚠️ **Importante**: Apps instalados via Apple ID gratuita expiram em **7 dias**. Quando expirar, é só repetir os passos 3 e 4 (Sideloadly) pra renovar. Pra renovação automática sem PC, usa o **AltStore** em vez do Sideloadly.

## Como atualizar o app

1. Edita o arquivo `www/index.html` direto pelo GitHub (botão de lápis ✏️)
2. Ou mexe no `www/manifest.json` se precisar mudar ícone/nome
3. Faz **commit** → push automático dispara novo build
4. Aguarda ~5 min na aba **Actions**
5. Baixa o novo IPA e reinstala no iPhone (Sideloadly substitui o anterior)

## Estrutura dos arquivos

```
catedral-ios/
├── www/                       ← SEU APP (edite aqui)
│   ├── index.html             ← código principal
│   ├── manifest.json          ← config PWA (nome, ícone, cor)
│   ├── icone.png              ← ícone do app
│   └── logo500.png            ← logo secundária
├── capacitor.config.json      ← config do Capacitor
├── package.json               ← dependências Node
├── .github/
│   └── workflows/
│       └── build-ios.yml      ← workflow do GitHub Actions (não mexer)
├── .gitignore                 ← arquivos ignorados
└── README.md                  ← este arquivo
```

## Mudar o IP do Holyrics

Se o IP da máquina com Holyrics mudar (ex: `192.168.10.178` → outro):

1. Edita `www/index.html` no GitHub
2. Procura (Ctrl+F) por `192.168.10.178`
3. Troca pelo IP novo (são 3 lugares)
4. Commit → push → novo build

## Problemas comuns

**App não conecta no Holyrics**
- Verifica se iPhone e PC estão no **mesmo Wi-Fi**
- Confirma que o popup de "Rede Local" foi aceito
- Testa se o IP do Holyrics responde do navegador do PC: `http://192.168.10.178:4455/api/GetCurrentPresentation?token=SEU_TOKEN`

**App expira e não abre mais**
- Refaz a instalação pelo Sideloadly (passo 3 acima)
- Ou instala o **AltStore** no PC pra renovar automaticamente

**Build do GitHub Actions falha**
- Vai na aba **Actions** → clica no build vermelho ❌
- Lê o log de erro
- Me chama aqui que eu te ajudo a resolver

---

Feito com 💜 pra Catedral. Dúvidas? Me chama.

# 📱 Guia de Empacotamento Android (.APK / .AAB) via Bubblewrap (TWA)

Este guia descreve o processo passo a passo para compilar o **FinanceTracker** num pacote Android instalável (`.apk` ou `.aab` para Google Play Store) utilizando **Trusted Web Activity (TWA)** e a CLI oficial **Bubblewrap** da Google.

---

## 1. Pré-requisitos

1. **Node.js** (versão 18 ou superior) instalado na máquina.
2. **Java Development Kit (JDK 17)** e **Android SDK** (o próprio Bubblewrap oferece o download automático caso não estejam instalados).
3. A aplicação já publicada em HTTPS (ex.: `https://finance-tracker-blond-ten.vercel.app`) servindo:
   - Manifesto PWA em `/manifest.json`
   - Service Worker em `/sw.js`
   - Digital Asset Links em `/.well-known/assetlinks.json`

---

## 2. Instalar o Bubblewrap CLI

No terminal, instale globalmente a ferramenta da Google:

```bash
npm install -g @bubblewrap/cli
```

---

## 3. Inicializar o Projeto TWA

Crie uma pasta dedicada para o build Android (fora ou dentro de uma pasta `android-twa/`) e aponte para o `manifest.json` em produção:

```bash
mkdir finance-tracker-android
cd finance-tracker-android
bubblewrap init --manifest="https://finance-tracker-blond-ten.vercel.app/manifest.json"
```

Durante o assistente interativo, confirme as seguintes opções sugeridas:
- **Application ID (Package Name):** `com.financetracker.app`
- **Host / Domain:** `finance-tracker-blond-ten.vercel.app`
- **Start URL:** `/login.html` ou `/index.html`
- **Display Mode:** `standalone`
- **Status Bar Color:** `#030712`
- **Keystore Path:** aceite a criação de uma nova chave `android.keystore` e defina uma palavra-passe segura.

---

## 4. Extrair a Impressão Digital SHA-256 e Validar o Digital Asset Links

Para que o Android abra a aplicação **em ecrã inteiro nativo (sem a barra de endereços do Chrome)**, o ficheiro `/.well-known/assetlinks.json` no servidor precisa conter o fingerprint `SHA-256` da sua chave de assinatura (`android.keystore`):

```bash
keytool -list -v -keystore ./android.keystore -alias android
```

Copie o valor `SHA256:` exibido (ex.: `14:6D:E9:7D:...`) e atualize os ficheiros:
- `.well-known/assetlinks.json`
- `frontend/.well-known/assetlinks.json`

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.financetracker.app",
      "sha256_cert_fingerprints": [
        "SUA_IMPRESSAO_DIGITAL_SHA256_AQUI"
      ]
    }
  }
]
```

Faça `git push` para publicar a atualização na Vercel.

---

## 5. Gerar o `.APK` e `.AAB`

Com o projeto configurado, execute:

```bash
bubblewrap build
```

Ao concluir, o Bubblewrap irá gerar:
- `app-release-signed.apk` — Pronto para instalar diretamente em qualquer telemóvel Android!
- `app-release-bundle.aab` — Pronto para envio à Google Play Console.

---

## 6. Instalar no Telemóvel via ADB (Opcional)

Se estiver com o telemóvel conectado via USB (com *Depuração USB* ativa):

```bash
bubblewrap install
```

Ou envie o ficheiro `app-release-signed.apk` para o telemóvel (via WhatsApp, Google Drive ou cabo USB) e toque para instalar.

# 🤖 Guia de Empacotamento Android (.APK) — FinanceTracker

Este guia explica como transformar o PWA do **FinanceTracker** hospedado na Vercel (`https://finance-tracker-blond-ten.vercel.app`) em um aplicativo nativo Android (`.apk` / `.aab`) utilizando **Bubblewrap (TWA oficial da Google)** ou **PWABuilder**.

---

## 🚀 Método 1: PWABuilder (Mais Rápido — Sem Instalar Java/Android SDK)

O **PWABuilder** (mantido pela Microsoft) gera o arquivo `.apk` pronto para instalar no seu celular ou publicar na Google Play Store diretamente pela nuvem:

1. Acesse: **[pwabuilder.com](https://www.pwabuilder.com/)**
2. Insira a URL da sua aplicação na Vercel:
   ```
   https://finance-tracker-blond-ten.vercel.app
   ```
3. O PWABuilder validará automaticamente o `manifest.json`, `sw.js` e os ícones de alta resolução já configurados.
4. Clique em **"Package for Stores"** > **Android**.
5. Selecione a opção **"Generate APK / Package"**:
   * O sistema fornecerá o download de um arquivo `.zip` contendo:
     * `app-release-signed.apk` (para instalar diretamente no seu telemóvel Android);
     * O fingerprint SHA-256 para você atualizar o arquivo `frontend/.well-known/assetlinks.json`.
6. Envie o `.apk` para o celular via WhatsApp, Google Drive ou cabo USB e instale!

---

## 🛠️ Método 2: Bubblewrap CLI (TWA Oficial Google)

O **Bubblewrap** é a ferramenta oficial do Google Chrome Labs para compilar PWAs como **Trusted Web Activity (TWA)**.

### Pré-requisitos:
* **Node.js** 18+ instalado;
* **Java Development Kit (JDK 17 ou 21)** instalado;
* **Android SDK Command-line Tools**.

### Passo a Passo:

1. **Instale a CLI global do Bubblewrap:**
   ```bash
   npm install -g @bubblewrap/cli
   ```

2. **Inicialize o projeto Android a partir do Manifest:**
   ```bash
   bubblewrap init --manifest https://finance-tracker-blond-ten.vercel.app/manifest.json
   ```
   * O Bubblewrap lerá as cores (`#00ffcc`), nome, ícones e URLs automaticamente.
   * Ele criará um arquivo `android.keystore` para assinar o aplicativo e exibirá a sua chave **SHA-256 Fingerprint**.

3. **Atualize o arquivo `assetlinks.json`:**
   Copie a chave SHA-256 exibida pelo Bubblewrap e cole em `frontend/.well-known/assetlinks.json`:
   ```json
   [
     {
       "relation": ["delegate_permission/common.handle_all_urls"],
       "target": {
         "namespace": "android_app",
         "package_name": "com.financetracker.app",
         "sha256_cert_fingerprints": [
           "SUA_CHAVE_SHA256_AQUI"
         ]
       }
     }
   ]
   ```
   *(Isso remove a barra superior do navegador na inicialização do app no Android, dando aspecto 100% nativo).*

4. **Compile o arquivo APK:**
   ```bash
   bubblewrap build
   ```
   * O arquivo final estará em:
     `app-release-signed.apk`

5. **Instale no celular conectado via USB (Modo Desenvolvedor / ADB):**
   ```bash
   bubblewrap install
   ```

---

## ⚡ Método 3: Capacitor (Ionic)

Se preferir utilizar a infraestrutura do **Capacitor**:

```bash
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init FinanceTracker com.financetracker.app --web-dir frontend
npx cap add android
npx cap open android
```
No Android Studio, clique em **Build > Build Bundle(s) / APK(s) > Build APK(s)**.

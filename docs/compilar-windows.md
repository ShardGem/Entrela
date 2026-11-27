# Gerar e distribuir o Entrela no Windows

O aplicativo mantém a versão `0.27.0`. O primeiro release para download utiliza essa identificação. O build é feito no Windows x64 com Python 3.12; PyInstaller inclui o interpretador, o motor científico, as DLLs, os plugins Qt, as fontes e os ícones.

## 1. Preparar o computador

Instale [Python 3.12 para Windows x64](https://www.python.org/downloads/windows/), Git e, para gerar o instalador, [Inno Setup 6](https://jrsoftware.org/isdl.php). O launcher `py` deve estar disponível.

No PowerShell, abra a pasta do projeto:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
py -3.12 --version
```

Se houver alterações locais, salve-as em sua branch antes de trocar. O script usa um ambiente separado, `.venv-release`, e não modifica o ambiente do PyCharm.

## 2. Compilar

Para gerar o aplicativo, o ZIP portátil e o instalador:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1 -Installer
```

`Bypass` vale apenas para esse processo. A política permanente do computador é preservada. O script instala as dependências fixadas, compila e verifica o executável; só depois prepara os arquivos de distribuição. A primeira compilação pode demorar pelo download e pela análise das bibliotecas científicas.

Para gerar apenas o portátil, omita `-Installer`. Em recompilações sem mudanças nas dependências, `-SkipInstall` reutiliza o ambiente preparado.

## 3. Encontrar os arquivos

| Arquivo | Finalidade |
|---|---|
| `dist/Entrela/Entrela.exe` | Executável, acompanhado de `_internal`. |
| `dist/release/Entrela-0.27.0-windows-x64-portatil.zip` | Pasta completa para extrair e usar. |
| `dist/release/Entrela-0.27.0-windows-x64-setup.exe` | Instalador para o usuário final. |
| `dist/release/SHA256SUMS.txt` | Integridade dos binários e do ZIP. |
| `dist/release/verificacao-portatil.json` | Resultado da verificação do executável gerado. |
| `dist/release/dependencias-build.txt` | Versões efetivas do ambiente de compilação. |

O ZIP precisa conter a pasta completa. Distribuir somente o executável de `dist/Entrela` deixa de fora bibliotecas e recursos. O instalador já reúne esses arquivos. Dados e preferências ficam no perfil do usuário, separados da pasta de instalação.

## 4. Compilar pelo GitHub

Em **Actions → Distribuição Windows → Run workflow**, escolha `main`. Ao terminar, baixe o artefato **Entrela-windows-x64**. Esse processo não exige configurar um ambiente Python no seu computador.

O workflow também instala o aplicativo em um diretório com espaços e acentos, abre o binário fora do checkout, confere o recibo e desinstala a cópia de teste. Isso acontece em um runner Windows, com o plugin nativo `windows` do Qt. Faça também uma abertura interativa em outro computador, preferencialmente sem Python instalado.

## 5. Publicar o release

Depois de integrar a versão à `main` e conferir os resultados de CI:

```powershell
git switch main
git pull --ff-only origin main
git tag -a v0.27.0 -m "Primeira distribuição desktop do Entrela"
git push origin v0.27.0
```

A tag precisa coincidir com a versão do motor e apontar para um commit da `main`. O workflow compila, testa e publica o release com instalador, ZIP, hashes e recibos. Se uma verificação falhar, a publicação não acontece; consulte **Actions → Distribuição Windows**.

Para outra versão, atualize os identificadores em `core/__init__.py` e `pyproject.toml`, acrescente `docs/releases/vNOVA_VERSAO.md` e use a tag correspondente. Preserve tags e arquivos já publicados.

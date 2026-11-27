# Capturas da revisão para distribuição

Capturas do aplicativo PySide6 em Linux com Qt offscreen e tema Azul Entrela. Os registros de Bell foram calculados em repositórios temporários apenas para verificar a interface; não são resultados da campanha da monografia. Nenhum dado pessoal foi utilizado.

| Tela | Janela | Texto |
|---|---|---|
| [Simulação](simulacao-1440.png) | 1440 × 900 | 15 px |
| [Histórico e circuito em consulta](historico-1440.png) | 1440 × 900 | 15 px |
| [Estudos e varreduras](estudos-1024-texto24.png) | 1024 × 768 | 24 px |
| [Configuração de ZNE](zne-1024-texto24.png) | 1024 × 768 | 24 px |

Estas quatro imagens são uma seleção da revisão de 96 capturas: 16 destinos, três temas e duas combinações de janela/texto. As dimensões de todos os arquivos foram conferidas. A aparência e a interação em Windows nativo permanecem no roteiro de validação do instalador.

Para reproduzir na raiz do checkout, com as dependências instaladas:

```sh
python scripts/preview_interface.py --all-pages --width 1440 --height 900 --output work/revisao-1440
python scripts/preview_interface.py --all-pages --width 1024 --height 768 --font-size 24 --output work/revisao-1024
```

Os diretórios de saída preservam os arquivos anteriores em `docs/screenshots/`.

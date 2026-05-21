# automacao-boletos

Automacao em Python para Windows que le boletos em PDF, extrai os dados principais e organiza os arquivos processados.

Esta e a Etapa 1. Ainda nao envia WhatsApp e nao integra com ERP.

## Requisitos

- Python 3.12
- Windows PowerShell ou terminal equivalente

## Instalar dependencias

```powershell
cd "C:\Users\guthierre\Documents\New project 2\automacao-boletos"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Estrutura

```text
automacao-boletos/
  boletos/
    pendentes/
    processados/
    erro/
  logs/
  src/
    main.py
    pdf_reader.py
    boleto_parser.py
    file_manager.py
    logger_config.py
  requirements.txt
  .env.example
  README.md
```

## Como usar

Coloque os PDFs de boleto em:

```text
boletos/pendentes/
```

Rode:

```powershell
python src/main.py
```

Ao processar com sucesso, o PDF sera movido para:

```text
boletos/processados/
```

Se falhar, sera movido para:

```text
boletos/erro/
```

## Saidas geradas

- Logs: `logs/app.log`
- JSON consolidado: `logs/resultados.json`
- Dados extraidos tambem aparecem no terminal

Exemplo de saida:

```json
{
  "nome_pagador": "RODRIGO PULINI",
  "cnpj_pagador": "03.652.501/0004-93",
  "cnpj_normalizado": "03652501000493",
  "valor": "908.95",
  "vencimento": "20/05/2026",
  "linha_digitavel": "34191.12184 70418.798214 70061.730001 4 14520000090895"
}
```

## Observacao sobre o CNPJ do pagador

O parser procura especificamente um bloco textual associado a `Pagador` ou `Sacado`.
Ele ignora blocos com termos como `Beneficiario`, `Cedente`, `Banco` e `Emissor` antes de capturar o CNPJ.

PDFs de boleto podem variar bastante de layout. Se algum banco vier com um formato diferente, coloque o arquivo em `boletos/pendentes/` e rode novamente para analisarmos o log e ajustar o parser.

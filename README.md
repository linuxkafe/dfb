# dfb — Deck FlyBrain 

A compute framework for the **FlyBrain** autonomous flight decision system, running on Steam Deck (x86_64 Linux, AMD APU) with Vulkan acceleration.

## Overview

This project provides a Vulkan compute engine and a neural co-processor prototype for the FlyBrain, running on Steam Deck hardware, accessible remotely via SSH.

## Architecture

- **Client** (development machine): requests, UI, orchestration
- **Server** (Steam Deck via SSH): Vulkan compute service, FlyBrain neural inference

## Quick Start

```bash
make setup      # install dependencies
make check      # run quality gates (lint, test, safety)
make deploy-deck  # deploy service to Steam Deck
```

## Vulkan Compute Engine

Located in `src/dfb/vulkan_engine.py` — a ctypes-based Vulkan 1.3 wrapper with:
- Two-pass compute pipeline (hidden + output shaders)
- Per-submission fencing for correct pass ordering
- Verified on Steam Deck RADV (VANGOGH, API 1.4.330)

## Neural Co-Processor (sim/)

A CPU-only neural co-processor prototype (`sim/`):

- `fly_coprocessor.py` — E-PG ring attractor, mushroom body with DAN plasticity, octopamine habituation
- `semantic_encoder.py` — text → topic angle with pre-synaptic habituation
- `neuro_to_ollama.py` — connectome state → Ollama parameters (temperature, num_predict, context-switch notes)
- `chat_cli.py` — interactive CLI with `++`/`--` feedback, telemetry line
- `test_coprocessor.py` — 13 offline validation cases

```bash
# offline demo (mock Ollama)
python sim/chat_cli.py --mock

# live against Steam Deck Ollama
python sim/chat_cli.py --base-url http://steamdeck:11434 --model llama3.1:8b
```

Telemetry format: `[Bússola: 42° | Alerta (Oct): 0.78 | Afinidade: +0.35 | Temp: 0.65]`

## 🧠 Coprocessador Biológico: Deteção de Insistência (Circuito Giant Fiber)

Este projeto integra uma emulação dos circuitos neuronais da *Drosophila* (especificamente o **Neurónio Gigante de Fuga - Giant Fiber**) para gerir a dinâmica de diálogo em conversas quotidianas sem depender de classificadores pesados de sentimento.

### Como Funciona
* **Acumulação de Potencial:** Mensagens repetitivas, frustradas ou loops sem resolução aumentam a voltagem da membrana do circuito biológico.
* **Disparo de Fuga:** Quando o potencial atinge o limiar crítico (0.5), o assistente corta automaticamente explicações prolixas e adota um tom estritamente direto e focado na resolução imediata.
* **Recuperação:** Diálogos construtivos e pausas naturais permitem o decaimento passivo do potencial.

### Exemplo Prático de Utilização (CLI)

```text
Utilizador: Como faço para listar processos a correr no porto 8080?
[Potencial GF: 0.05 | Modo: Normal | Temp: 0.60]
Bot: Podes verificar quais os processos a escutar nessa porta utilizando o utilitário lsof ou o ss com privilégios adequados:
1. Com lsof: `lsof -i :8080`
2. Com ss: `ss -tulpn | grep :8080`
Qualquer um deles mostrará o PID associado ao serviço.

Utilizador: Não deu nada.
[Potencial GF: 0.35 | Modo: Normal | Temp: 0.50]
Bot: Se o comando não devolveu saída, confirma se estás a correr o comando com privilégios suficientes ou se a porta está mesmo ativa. Tenta com `sudo ss -tulpn | grep 8080`.

Utilizador: Nada outra vez, continua sem dar nada!
[Potencial GF: 0.82 | Modo: DISPARO DE FUGA | Temp: 0.10]
Bot: 
- Executa: `sudo ss -lnt` e verifica se o porto aparece listado na coluna de escuta.
- Se não aparecer, o serviço não está ativo. Queres arrancar o serviço ou verificar os logs do sistema?
```

## Development

```bash
make test   # run test suite (pytest)
make lint   # ruff check
make format # ruff format
```

## TODO

- [ ] Persistent memory/DB for co-processor state
- [ ] Streaming UI for chat_cli
- [ ] Real-time audio integration
- [ ] Move simulation to Vulkan compute kernel (un-defer T005)
- [ ] CI: add codecov token for coverage upload
- [ ] Safety gate closure for gRPC surface (T013)

## Hardware Target

Steam Deck (AMD APU, VANGOGH GPU, RADV Vulkan driver). No FC firmware changes — integration via MAVLink/CRSF only.

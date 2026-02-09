<!--
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
-->
# AVF — Adaptive Vivo File

AVF é um formato de arquivo append-only para memória viva e reconstrução cognitiva via event-sourcing. Ele combina chunks binários assinados com snapshots para replay rápido e integrações com LLMs.

## Arquitetura resumida
- **Formato append-only**: chunks com `MAGIC + TYPE + TIMESTAMP + SIZE + DATA + CHECKSUM`.
- **Writer atômico**: gravação única + `fsync` para minimizar corrupção parcial.
- **Reader streaming**: itera chunk a chunk, validando checksum.
- **Snapshots**: checkpoint automático a cada N eventos, com replay rápido.
- **Core cognitivo**: reconstrói estado e grava eventos, identidade e personalidade.

## Exemplos de API
```python
from runtime.avf_io import AVFAppendWriter, AVFStreamReader
from runtime.avf_core import CognitiveCore

writer = AVFAppendWriter("/mnt/data/sample.avf")
writer.append_chunk("EVENT", {"type": "concept", "value": "alpha"})

reader = AVFStreamReader("/mnt/data/sample.avf")
for chunk in reader.stream():
    print(chunk["type"], chunk["payload"])

core = CognitiveCore()
core.reconstruct_from_avf("/mnt/data/sample.avf")
```

## Rodar no Colab
1. Abra `examples/demo_colab.ipynb` no Google Colab.
2. Execute as células em ordem (instalação, geração de AVF, replay e métricas).

## Rodar testes
```bash
pytest tests/test_io.py
```

## Motivos de design
- **Event-sourcing** simplifica replay e auditoria.
- **Snapshots** reduzem tempo de reconstrução.
- **Append-only** minimiza riscos de perda por gravação parcial.

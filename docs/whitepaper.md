<!--
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
-->
# AVF Whitepaper (Resumo técnico)

AVF define um formato de arquivo append-only com chunks binários verificáveis para armazenar eventos cognitivos e checkpoints. O cabeçalho de cada chunk contém metadados e um checksum SHA-256 para detectar corrupção. Snapshots são gerados periodicamente para reduzir o tempo de replay.

O sistema se organiza em:
- **AVF I/O**: escrita atômica com `fsync` e leitura streaming.
- **Core Cognitivo**: aplica eventos, persiste identidade e reconstrói estado.
- **Snapshots**: checkpoint automático e replay a partir do último snapshot.
- **LLM Adapter**: integração plugável para gerar respostas e gravar eventos.

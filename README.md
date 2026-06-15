# GW Express - Aplicação Web Completa de Roteirização

## Recursos
- Upload de Excel/CSV.
- Banco SQLite local.
- Dashboard web.
- Roteirização por proximidade.
- Cluster por bairro e coordenadas.
- Respeito ao SPR planejado.
- Capacidade máxima e mínima.
- Limitador de KM por rota.
- Realocação de baixa ADO.
- Rotas válidas e não viáveis.
- Links Google Maps por rota e por pedido.
- Romaneio para impressão.
- Correção simples de rota.
- Exportação CSV.

## Como executar no Windows

1. Instale Python 3.11 ou superior.
2. Abra o Prompt de Comando dentro desta pasta.
3. Rode:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. Abra no navegador:

```text
http://127.0.0.1:8000
```

## Configuração padrão GW Express

- Capacidade máxima: 95
- Capacidade mínima: 70
- KM máximo: 35
- Distância máxima entre pedidos: 1.5 km
- Origem: Rua Desembargador Enock Santiago, 91 - Aracaju/SE

## Observação
O KM é estimado por latitude/longitude. O Google Maps calcula o trajeto real ao abrir o link.

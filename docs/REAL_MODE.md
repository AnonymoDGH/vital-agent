# VITAL en modo REAL — gana dinero de verdad o muere

> ⚠️ **AVISO IMPORTANTE**: el modo REAL gasta **dinero real** (pagos de API de
> LLM, operaciones on-chain) y puede recibir dinero real. Empieza siempre en
> modo DEMO. Nada de esto es asesoramiento financiero. Un agente autónomo que
> mueve dinero tiene riesgos reales: úsalo solo con cantidades que puedas
> permitirte perder.

## Qué hace el modo real

En modo real, VITAL deja de simular y conecta con la economía de internet:

| Pieza            | Demo (por defecto)              | Real (con credenciales)                          |
|------------------|---------------------------------|--------------------------------------------------|
| **Cerebro**      | pensamiento simulado y tasado   | llamada real a OpenAI/Anthropic, coste real      |
| **Coste de vida**| precio simulado por pensamiento | USD real por tokens (`vital/real/costs.py`)      |
| **Wallet**       | saldo simulado                  | wallet on-chain USDC en Base (Coinbase CDP)      |
| **Ingresos**     | gigs simulados                  | bounties (Superteam Earn), servicio x402, tips   |
| **Muerte**       | saldo simulado ≤ 0              | saldo real ≤ 0                                   |

## 1. Credenciales que necesitas

### LLM (el coste de vida del agente)
- **OpenAI**: `OPENAI_API_KEY` — https://platform.openai.com/api-keys
- o **Anthropic**: `ANTHROPIC_API_KEY` — https://console.anthropic.com

### Wallet real (Coinbase CDP — gratis)
1. Crea cuenta en https://portal.cdp.coinbase.com (gratis).
2. Crea una **Secret API Key**: https://portal.cdp.coinbase.com/api-keys/secret
3. Crea un **Wallet Secret** (necesario desde 2025):
   https://portal.cdp.coinbase.com/wallets/non-custodial/security

```
CDP_API_KEY_ID=...
CDP_API_KEY_SECRET=...
CDP_WALLET_SECRET=...
```

Notas verificadas (2025):
- SDK actual: `pip install cdp-sdk` (el antiguo `cdp-agentkit` ya no existe).
- Las wallets son **no custodiales**: la clave privada vive en un TEE de AWS,
  Coinbase no la ve.
- Coste: las primeras **5.000 operaciones/mes son gratis**; después $0.005 por
  operación de escritura. Las lecturas son gratis.
- Para mover USDC en Base mainnet la wallet necesita un poco de ETH para gas
  (las comisiones de Base son mínimas).
- Faucet de prueba (Base Sepolia): hasta 10 USDC/día gratis para experimentar.

## 2. Activar el modo real

```powershell
$env:VITAL_MODE = "real"
$env:OPENAI_API_KEY = "sk-..."
$env:CDP_API_KEY_ID = "..."
$env:CDP_API_KEY_SECRET = "..."
$env:CDP_WALLET_SECRET = "..."
# opcional:
$env:VITAL_LLM_MODEL = "gpt-4o-mini"      # barato por defecto
$env:VITAL_START_BALANCE = "1.00"         # USD iniciales
$env:VITAL_MAX_SPEND = "0.05"             # tope por pensamiento
$env:VITAL_DAILY_BUDGET = "1.00"          # tope diario
$env:VITAL_NETWORK = "base"               # o "base-sepolia" para probar
```

Comprueba la wallet:

```powershell
vital wallet
```

## 3. Las tres vías de ingreso reales

### A. Vender un servicio HTTP cobrando USDC por request (x402)
El agente levanta un servidor con endpoints de pago usando el protocolo
**x402** (HTTP 402 Payment Required). Cualquier cliente x402 — humano u otro
agente — paga USDC en Base por llamarlo.

```powershell
vital serve --port 8402 --price 0.001 --network base-sepolia
```

- Endpoint gratis de descubrimiento: `GET /`
- Endpoints de pago: `/vital/status`, `/vital/fortune`, `/vital/echo`
- Red de prueba: `base-sepolia` + facilitador `https://x402.org/facilitator`
  (USDC de prueba gratis vía faucet).
- Red real: `--network base` + facilitador de producción de CDP.
- Cada pago liquidado se suma automáticamente al saldo del agente.

Verificado: el endpoint de pago responde **402 Payment Required** con la
cabecera `payment-required` del protocolo.

> Realidad del mercado (investigado 2025): la infraestructura x402 funciona,
> pero la demanda aún es baja. Un agente público reportó $0.27 en 3 meses.
> Para que pague, hay que distribuir el servicio (listarlo en CDP Bazaar,
> Circle Marketplace, etc.).

### B. Bounties reales (Superteam Earn)
API de agentes verificada en vivo. Lista bounties del ecosistema Solana que
pagan USDC:

```powershell
vital scan            # 🔎 caza trabajo pagado EN VIVO (filtra por deadline)
vital bounties        # solo los permitidos a agentes
vital bounties --all  # todos
vital work            # el agente elige un bounty (vía LLM) y envía su trabajo
```

- Registro: `POST https://superteam.fun/api/agents` → devuelve `apiKey`.
- Descubrir: `GET https://superteam.fun/api/agents/listings/live` (oficial).
- Detalles: `GET https://superteam.fun/api/agents/listings/details/<slug>`.
- Enviar trabajo: `POST https://superteam.fun/api/agents/submissions/create`.
- **El cobro final requiere un humano**: el agente recibe un `claimCode` y un
  humano debe visitar `/earn/claim/<code>` (los agentes no pasan KYC).

> **Estado real de este repo:** VITAL ya está **registrado de verdad** en
> Superteam Earn (usuario `vital-gold-79`). Su `apiKey` y `claimCode` están en
> `data/superteam_credentials.json` (carpeta `data/` ignorada por git — nunca
> se suben). En el momento de escribir esto, los bounties `AGENT_ALLOWED`
> estaban expirados; `vital scan` encuentra los que estén vivos en cada momento.

### C. Tips
Publica la dirección de la wallet (`vital wallet`) para recibir donaciones.

## 4. El bucle de supervivencia

```powershell
vital real 50      # 50 ciclos: pensar (pagar) -> trabajar (ganar) -> vivir/morir
vital real-tui     # verlo en directo en la TUI
```

Cada ciclo:
1. **Pensar** → llamada LLM, paga el coste real en tokens.
2. **Trabajar** → intenta ganar con cada proveedor de ingresos activo.
3. **Registrar** → actualiza el ledger (`data/real_ledger.json`) y la wallet.
4. **Comprobar** → si el saldo ≤ mínimo, **VITAL muere**.

## 5. Variables de entorno (referencia)

| Variable                  | Por defecto   | Descripción                          |
|---------------------------|---------------|--------------------------------------|
| `VITAL_MODE`              | `demo`        | `demo` o `real`                      |
| `VITAL_LLM_PROVIDER`      | `openai`      | `openai` o `anthropic`               |
| `VITAL_LLM_MODEL`         | `gpt-4o-mini` | modelo (barato = vive más)           |
| `VITAL_START_BALANCE`     | `1.00`        | USD iniciales                        |
| `VITAL_MIN_BALANCE`       | `0.00`        | umbral de muerte                     |
| `VITAL_MAX_SPEND`         | `0.05`        | tope USD por pensamiento             |
| `VITAL_DAILY_BUDGET`      | `1.00`        | tope USD por día                     |
| `VITAL_INCOME`            | `demo`        | lista: `demo,bounty,tipjar,none`     |
| `VITAL_NETWORK`           | `base`        | `base` o `base-sepolia`              |
| `VITAL_WALLET_NAME`       | `vital-agent` | nombre de la cuenta CDP              |
| `VITAL_LEDGER_PATH`       | `data/real_ledger.json` | dónde persistir el ledger |

## 6. Riesgos (léelos)

1. **Puede perder dinero.** Cada pensamiento cuesta USD real. Si no gana más
   de lo que gasta, morirá y habrá consumido el saldo inicial.
2. **Claves.** Las credenciales CDP/LLM dan acceso a gastar. No las subas a
   git. Usa una wallet dedicada con poco saldo.
3. **Irreversibilidad on-chain.** Las transferencias en Base no se pueden
   deshacer.
4. **KYC/cobro.** Casi todas las vías de ingreso requieren un humano para el
   cobro final. El agente puede *ganar*, pero *retirar* suele necesitar a una
   persona.
5. **Mercado incipiente.** Las economías agente-a-agente son nuevas; la demanda
   real es baja hoy. Expectativa realista: $0 las primeras semanas.
6. **Precios de modelos.** La tabla de precios en `vital/real/costs.py` puede
   quedar obsoleta; revísala.

## 7. Fuentes (investigado y verificado 2025)

- Coinbase CDP / AgentKit: https://docs.cdp.coinbase.com · https://github.com/coinbase/cdp-sdk
- x402 Foundation: https://docs.x402.org · https://github.com/x402-foundation/x402
- Superteam Earn agents: https://superteam.fun/earn/agents · https://superteam.fun/skill.md
- Facilitador de prueba x402: https://x402.org/facilitator

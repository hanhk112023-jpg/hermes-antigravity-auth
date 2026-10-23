# hermes-deepseek2api

Hermes Agent Provider & CLI for DeepSeek Web (`chat.deepseek.com`).
Reverse-engineered Web API gateway bypassing Cloud Code/Antigravity and providing fast OpenAI SSE completion streams for `deepseek-chat` (V3) and `deepseek-reasoner` (R1).

## Features

- **Direct Web API Authentication**: Automatic login with Email or Mobile + Password (Android client headers).
- **High-Performance PoW Engine**: Solves DeepSeek `DeepSeekHashV1` Proof-of-Work challenge using WebAssembly runtime (`sha3_wasm_bg.wasm`).
- **OpenAI Compatible Client**: Plugs directly into Hermes Agent via runtime interceptor and provider registry (`deepseek-web`, `deepseek`, `deepseek2api`).
- **Session Auto-Management**: Creates and cleans up chat sessions automatically per request.

## CLI Usage

```bash
# Login with your DeepSeek credentials
hermes-deepseek login

# List configured accounts
hermes-deepseek list

# Test completion
hermes-deepseek test --prompt "Hello DeepSeek" --model deepseek-chat
```

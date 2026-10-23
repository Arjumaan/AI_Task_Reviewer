# Benchmark Local Ollama and Speech Engines
Write-Host ">>> Running Local FOSS AI Benchmarks (Ollama + TTS)..." -ForegroundColor Cyan
.venv\Scripts\Activate.ps1
python poc/test_tts.py
python -c "
import asyncio, httpx, time

async def bench():
    print('Testing Ollama llama3.2:1b latency...')
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'llama3.2:1b',
                'prompt': 'Brief an intern on implementing a thread-safe LRU cache in Python in 50 words.',
                'stream': False
            }
        )
        elapsed = time.perf_counter() - start
        if res.status_code == 200:
            data = res.json()
            eval_count = data.get('eval_count', 0)
            tok_per_sec = eval_count / (data.get('eval_duration', 1) / 1e9)
            print(f'Ollama generation complete: {eval_count} tokens in {elapsed:.2f}s ({tok_per_sec:.2f} tokens/sec)')
            print(f'Response: {data.get(\"response\", \"\")[:120]}...')
        else:
            print(f'Ollama returned status {res.status_code}')

asyncio.run(bench())
"

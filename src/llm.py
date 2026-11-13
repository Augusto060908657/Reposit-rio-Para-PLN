"""Cliente do LLM local via Ollama (HTTP) e um LLM de mentira (stub) usado só para testar o código sem GPU."""
import re, time
import requests


class OllamaChat:
    def __init__(self, modelo="qwen2.5:7b", host="http://localhost:11434", temperatura=0.2,
                 num_ctx=4096, max_tokens=220, timeout=180):
        self.modelo, self.host, self.timeout = modelo, host.rstrip("/"), timeout
        self.opcoes = dict(temperature=temperatura, num_ctx=num_ctx, num_predict=max_tokens)

    def chat(self, mensagens, json_only=False):
        corpo = dict(model=self.modelo, messages=mensagens, stream=False, options=self.opcoes, keep_alive="30m")
        if json_only:
            corpo["format"] = "json"
        t0 = time.perf_counter()
        r = requests.post(f"{self.host}/api/chat", json=corpo, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"].strip(), time.perf_counter() - t0


class StubLLM:
    """NÃO é um modelo de linguagem. Só devolve respostas fixas para testar o fluxo sem GPU. Nunca usar nos resultados."""
    modelo = "stub"

    def chat(self, mensagens, json_only=False):
        t0 = time.perf_counter()
        ultimo = mensagens[-1]["content"].lower()
        if json_only:
            return '{"tipo": "buraco", "endereco": "rua Augusta, 520", "gravidade": "alta", "detalhes": "teste"}', 0.0
        if re.search(r"chover|receita|bolsa|python|jogo", ultimo):
            return "Não posso ajudar com isso, eu só ajudo com problemas urbanos como buraco, árvore e iluminação.", time.perf_counter() - t0
        if "buraco" in ultimo or "rua" in ultimo:
            return "Entendi. Fica na rua Augusta, número quinhentos e vinte. Posso registrar o pedido?", time.perf_counter() - t0
        return "Pedidos de serviço são feitos pelo SP156, telefone 156.", time.perf_counter() - t0

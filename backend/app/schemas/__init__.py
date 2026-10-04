"""Schemas (Pydantic): o CONTRATO da API, ou seja, o formato do JSON que entra e sai.

Por que não devolver as entidades do domínio direto?
- o domínio pode mudar por dentro (renomear um campo, trocar uma lista por um
  dicionário) sem quebrar o frontend: só o método `de_dominio` muda;
- o schema decide o que é público: o texto do OCR ou detalhes internos não
  precisam sair na API;
- o FastAPI usa os schemas para validar a resposta e gerar a documentação
  automática em /docs (OpenAPI).

Cada schema tem um `de_dominio(...)`: a conversão domínio -> JSON fica explícita
e num lugar só.
"""

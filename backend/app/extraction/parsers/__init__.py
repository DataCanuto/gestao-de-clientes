"""Parsers: funções PURAS que recebem texto e devolvem valores.

Por que funções e não classes? Um parser não guarda estado nem depende de
configuração: entra texto, sai valor. Uma função é a forma mais simples de
expressar isso, e é trivial de testar (tests/extraction/test_parsers_*.py).
Classes aparecem onde há estado ou dependências a injetar (readers, extractors,
pipeline).

Os padrões regex são constantes de módulo (em MAIÚSCULAS) para que fiquem
visíveis, documentados e reaproveitáveis nos testes.
"""

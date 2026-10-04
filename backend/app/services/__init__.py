"""Services: regras de aplicação (os "casos de uso").

Um service coordena domínio, extração, armazenamento e repositório para cumprir
uma tarefa ("receber um lote", "processar um lote"). Não conhece HTTP: recebe e
devolve objetos Python e sinaliza problemas com exceções próprias
(services/exceptions.py), que a camada de API traduz em códigos HTTP.
"""

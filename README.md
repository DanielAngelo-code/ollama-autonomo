# Ollama Server Admin

Este projeto permite que você gerencie um servidor Ubuntu conversando com um assistente Ollama diretamente pelo terminal SSH.

## Pré-requisitos

1. **Ollama instalado**: Certifique-se de que o Ollama está rodando no seu servidor.
2. **Modelo Llama 3**: O script usa o modelo `llama3`. Baixe-o com:
   ```bash
   ollama pull llama3
   ```
3. **Python 3.x**: O script é escrito em Python.

## Instalação

1. Clone ou baixe este repositório no seu servidor Ubuntu.
2. Crie um ambiente virtual (recomendado para evitar erros de sistema):
   ```bash
   python3 -m venv venv
   ```
3. Ative o ambiente virtual:
   ```bash
   source venv/bin/activate
   ```
4. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

Com o ambiente virtual ativado:
```bash
python ollama_admin.py
```

### Configurar como Shell SSH

Para que este script seja carregado automaticamente quando você entrar no servidor via SSH, use o caminho do Python do ambiente virtual:

**Recomendado (Adicionar ao .bashrc):**
```bash
echo "/caminho/completo/para/ollama-autonomo/venv/bin/python /caminho/completo/para/ollama-autonomo/ollama_admin.py && exit" >> ~/.bashrc
```
*Substitua `/caminho/completo/para/ollama-autonomo/` pelo caminho real onde você salvou o projeto.*

*Isso fará com que o script inicie assim que você logar e encerre a sessão SSH quando você sair do assistente.*

## Segurança
- O assistente agora é **autônomo** e executa comandos diretamente para agilizar o gerenciamento.
- **Cuidado:** Como não há mais confirmação manual, use comandos claros e evite pedir ações destrutivas a menos que tenha certeza.

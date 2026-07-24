# Geracao do instalador

Execute, na raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

O processo gera:

- `dist\Prontu\`: aplicativo empacotado para validacao local;
- `release\Prontu-Setup-<versao>.exe`: instalador entregue ao cliente.

Somente `SUPABASE_URL` e `SUPABASE_KEY` sao copiadas do `.env` para o
aplicativo. Tokens de sessao, senhas, chaves administrativas e o arquivo `.env`
completo nao sao distribuidos.

Para alterar a versao do aplicativo, edite o arquivo `VERSION` antes de gerar
uma nova compilacao.

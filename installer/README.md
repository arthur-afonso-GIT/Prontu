# Geracao do instalador

Execute, na raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1
```

O processo gera:

- `dist\Prontu\`: aplicativo empacotado para validacao local;
- `release\Prontu-Setup-<versao>.exe`: instalador entregue ao cliente.

Antes de criar os arquivos, o processo executa todos os testes automatizados e
valida se a versão empacotada contém a interface QML e os recursos obrigatórios.
Se alguma dessas verificações falhar, nenhum instalador é gerado.

Somente `SUPABASE_URL` e `SUPABASE_KEY` sao copiadas do `.env` para o
aplicativo. Tokens de sessao, senhas, chaves administrativas e o arquivo `.env`
completo nao sao distribuidos.

Para alterar a versao do aplicativo, edite o arquivo `VERSION` antes de gerar
uma nova compilacao.

## Assinatura digital

O build pode assinar o executavel do Prontu e o instalador com um certificado
publicamente confiavel de assinatura de codigo. Um certificado autoassinado
nao deve ser usado na versao entregue aos clientes, pois o Windows o trata
praticamente como um arquivo sem assinatura.

Antes de assinar:

1. adquira um certificado de assinatura de codigo aceito pelo Windows;
2. instale o Windows SDK com o componente `Signing Tools for Desktop Apps`;
3. instale o certificado conforme as instrucoes da certificadora.

Se o certificado aparecer no repositorio de certificados do Windows, use a
impressao digital dele:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1 `
  -CertificateThumbprint "IMPRESSAO_DIGITAL_DO_CERTIFICADO" `
  -RequireSignature
```

O parametro `-RequireSignature` interrompe o build se a assinatura nao puder
ser criada ou validada. Assim, uma versao oficial nao e publicada sem querer
como arquivo nao assinado.

Se a certificadora fornecer um arquivo PFX, a senha deve ser mantida somente
na variavel temporaria `PRONTU_SIGNING_PFX_PASSWORD`, nunca salva no projeto:

```powershell
$env:PRONTU_SIGNING_PFX_PASSWORD = "senha-do-certificado"
powershell -ExecutionPolicy Bypass -File .\scripts\build_installer.ps1 `
  -CertificatePfxPath "C:\caminho\certificado.pfx" `
  -RequireSignature
Remove-Item Env:\PRONTU_SIGNING_PFX_PASSWORD
```

O script usa SHA-256, adiciona carimbo de tempo e valida as assinaturas do
`Prontu.exe` e do instalador antes de concluir.

# Segurança e migração SaaS

## Faça assim, sem precisar saber SQL

1. No Supabase, abra **SQL Editor** e clique em **New query**.
2. Abra o arquivo `supabase/migrations/001_auth_audit_softdelete.sql` no projeto. Copie tudo, cole no editor e clique em **Run**. Aguarde a mensagem verde de sucesso.
3. Crie outra consulta. Repita com `supabase/migrations/002_rls_policies.sql` e clique em **Run**.
4. Em **Storage**, confira se o bucket se chama `fichas-anexos`. Se o nome for esse, não altere nenhum SQL.
5. Não é necessário entender nem editar as duas consultas: apenas execute cada arquivo inteiro, uma vez, na ordem acima.

## Ativação hospedada pelo Supabase

Você não precisa ter servidor próprio. A função `supabase/functions/ativar-consultorio/index.ts` roda dentro do Supabase.

1. Instale a Supabase CLI e execute `supabase login`.
2. Na pasta do projeto, execute `supabase link --project-ref SEU_ID_DO_PROJETO`.
3. Execute `supabase functions deploy ativar-consultorio --no-verify-jwt`.

As chaves `SUPABASE_URL`, `SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_ROLE_KEY` já existem para Functions hospedadas no Supabase; não é preciso criá-las manualmente. Nunca coloque a chave `service_role` no `.env` do aplicativo. O desktop já chama a função automaticamente usando `SUPABASE_URL` e a chave anônima.

## Provisionamento e RLS

A função do Supabase valida a chave, cria/atualiza uma identidade técnica por dispositivo e devolve uma sessão Auth. O desktop só usa essa sessão e a chave anônima. As políticas comparam o `consultorio_id` da linha ao vínculo de `auth.uid()` em `usuarios_consultorios`; Storage exige o mesmo ID como primeira pasta do objeto.

Teste antes de liberar: ative dois consultórios distintos, autentique cada um e tente selecionar, inserir, alterar e excluir uma linha e um anexo com o ID do outro. Todas as tentativas devem retornar vazio ou erro de RLS. Verifique também que `chaves_acesso` não é consultável pelo cliente e que `audit_logs` não aceita UPDATE, DELETE ou INSERT direto.

## Auditoria e dados clínicos

Triggers gravam alterações no banco e preservam versões anteriores de fichas preenchidas. Exclusão de pacientes e fichas é lógica; `DELETE` definitivo é bloqueado. Eventos de backup usam a RPC `registrar_audit_log`. Logs são imutáveis para a função do aplicativo.

## Backup

O backup é AES-256-GCM com chave derivada por scrypt da senha de recuperação, que não é enviada ao Supabase. Perder a senha impossibilita a restauração. Restaurações são aditivas e o modo seguro evita IDs e dados apagados; faça a restauração primeiro em um ambiente separado. A opção de anexos inclui também o conteúdo dos arquivos permitidos pelo RLS.

## Limites operacionais

RLS e criptografia são controles técnicos, não certificação de conformidade legal. Produção ainda exige revisão jurídica/LGPD, política de retenção, rotação/revogação operacional de chaves, monitoramento da Edge Function, limites de tentativa/rate limiting no gateway e testes de restauração periódicos. Em máquinas sem Credential Manager/DPAPI disponível, a sessão não é persistida em disco: será necessário ativar novamente ao reiniciar.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const headers = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
};

function resposta(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), { status, headers });
}

async function sha256(valor: string) {
  const bytes = new TextEncoder().encode(valor);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers });
  if (request.method !== "POST") {
    return resposta({ error: "Método não permitido." }, 405);
  }

  try {
    const body = await request.json();
    const codigoInformado = String(body.codigo ?? "").trim();
    const codigoNormalizado = codigoInformado.toUpperCase();
    const email = String(body.email ?? "").trim().toLowerCase();
    const senha = String(body.senha ?? "");

    if (!codigoNormalizado || !email.includes("@") || senha.length < 8) {
      return resposta({ error: "Confira o código, o e-mail e a senha." }, 400);
    }

    const url = Deno.env.get("SUPABASE_URL") ?? "";
    const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
    if (!url || !serviceRole || !anonKey) {
      return resposta({ error: "Serviço de convites indisponível." }, 500);
    }

    const admin = createClient(url, serviceRole, {
      auth: { persistSession: false, autoRefreshToken: false },
    });

    // Aceita convites antigos que tenham sido gravados antes da
    // normalização para letras maiúsculas.
    const hashes = Array.from(new Set([
      await sha256(codigoInformado),
      await sha256(codigoNormalizado),
    ]));

    const conviteResult = await admin
      .from("convites_equipe")
      .select("id,consultorio_id,nome,email,papel,expira_em")
      .ilike("email", email)
      .in("codigo_hash", hashes)
      .is("aceito_em", null)
      .is("revogado_em", null)
      .gt("expira_em", new Date().toISOString())
      .order("criado_em", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (conviteResult.error) {
      console.error("Erro ao consultar convite", conviteResult.error);
      return resposta({ error: "Não foi possível consultar o convite agora." }, 500);
    }
    const convite = conviteResult.data;
    if (!convite) {
      return resposta({
        error: "O código e o e-mail não correspondem a um convite ativo. Gere um novo convite e tente novamente.",
      }, 404);
    }

    // Se uma tentativa anterior criou o usuário, mas falhou antes de
    // concluir o vínculo, a nova tentativa reaproveita e finaliza a conta.
    let authUser: any = null;
    for (let pagina = 1; pagina <= 10 && !authUser; pagina += 1) {
      const usuarios = await admin.auth.admin.listUsers({ page: pagina, perPage: 1000 });
      if (usuarios.error) {
        console.error("Erro ao procurar usuário", usuarios.error);
        return resposta({ error: "Não foi possível preparar o acesso agora." }, 500);
      }
      authUser = usuarios.data.users.find(
        (usuario) => String(usuario.email ?? "").toLowerCase() === email,
      ) ?? null;
      if (usuarios.data.users.length < 1000) break;
    }

    let usuarioCriadoAgora = false;
    if (!authUser) {
      const criado = await admin.auth.admin.createUser({
        email,
        password: senha,
        email_confirm: true,
        user_metadata: { nome: convite.nome },
      });
      if (criado.error || !criado.data.user) {
        console.error("Erro ao criar usuário", criado.error);
        return resposta({ error: "Não foi possível criar o acesso deste e-mail." }, 500);
      }
      authUser = criado.data.user;
      usuarioCriadoAgora = true;
    } else {
      const atualizado = await admin.auth.admin.updateUserById(authUser.id, {
        password: senha,
        email_confirm: true,
        user_metadata: { ...authUser.user_metadata, nome: convite.nome },
      });
      if (atualizado.error) {
        console.error("Erro ao concluir usuário existente", atualizado.error);
        return resposta({ error: "Este e-mail já existe, mas o acesso não pôde ser concluído." }, 500);
      }
    }

    const vinculoAtual = await admin
      .from("usuarios_consultorios")
      .select("id")
      .eq("auth_user_id", authUser.id)
      .eq("consultorio_id", convite.consultorio_id)
      .maybeSingle();

    let erroVinculo = vinculoAtual.error;
    if (!erroVinculo && vinculoAtual.data?.id) {
      const atualizado = await admin
        .from("usuarios_consultorios")
        .update({
          papel: convite.papel,
          nome_exibicao: convite.nome,
          revogado_em: null,
        })
        .eq("id", vinculoAtual.data.id);
      erroVinculo = atualizado.error;
    } else if (!erroVinculo) {
      const inserido = await admin.from("usuarios_consultorios").insert({
        auth_user_id: authUser.id,
        consultorio_id: convite.consultorio_id,
        papel: convite.papel,
        nome_exibicao: convite.nome,
      });
      erroVinculo = inserido.error;
    }

    if (erroVinculo) {
      console.error("Erro ao vincular integrante", erroVinculo);
      if (usuarioCriadoAgora) await admin.auth.admin.deleteUser(authUser.id);
      return resposta({
        error: "Não foi possível vincular este acesso à clínica. Verifique se ainda existe uma vaga no plano.",
      }, 409);
    }

    const aceito = await admin
      .from("convites_equipe")
      .update({ aceito_em: new Date().toISOString() })
      .eq("id", convite.id)
      .is("aceito_em", null)
      .is("revogado_em", null);
    if (aceito.error) {
      console.error("Erro ao concluir convite", aceito.error);
      return resposta({ error: "O acesso foi criado, mas o convite não pôde ser concluído." }, 500);
    }

    const autenticacao = createClient(url, anonKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const login = await autenticacao.auth.signInWithPassword({ email, password: senha });
    if (login.error || !login.data.session) {
      console.error("Erro no primeiro login", login.error);
      return resposta({
        error: "O acesso foi criado. Use a aba Entrar com o e-mail e a senha informados.",
      }, 409);
    }

    const assinatura = await admin
      .from("assinaturas_consultorios")
      .select("plano,status,max_usuarios,expira_em,recursos_extras")
      .eq("consultorio_id", convite.consultorio_id)
      .maybeSingle();
    const clinica = await admin
      .from("chaves_acesso")
      .select("nome_clinica")
      .eq("consultorio_id", convite.consultorio_id)
      .limit(1)
      .maybeSingle();

    return resposta({
      access_token: login.data.session.access_token,
      refresh_token: login.data.session.refresh_token,
      expires_at: login.data.session.expires_at,
      auth_user_id: authUser.id,
      consultorio_id: convite.consultorio_id,
      nome_clinica: clinica.data?.nome_clinica ?? null,
      papel: convite.papel,
      plano: assinatura.data?.plano ?? "solo",
      status_assinatura: assinatura.data?.status ?? "ativa",
      max_usuarios: assinatura.data?.max_usuarios ?? 1,
      expira_em: assinatura.data?.expira_em ?? null,
      recursos_extras: assinatura.data?.recursos_extras ?? [],
    });
  } catch (error) {
    console.error("Erro inesperado ao aceitar convite", error);
    return resposta({ error: "Não foi possível aceitar o convite agora." }, 500);
  }
});

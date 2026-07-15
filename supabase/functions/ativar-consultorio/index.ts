/**
 * Servico de ativacao hospedado pelo Supabase.
 * Secrets ficam somente no painel Supabase, nunca no aplicativo desktop.
 */
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const headers = { "Content-Type": "application/json" };

function response(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), { status, headers });
}

function deviceEmail(consultorioId: number, deviceId: string) {
  const clean = deviceId.replace(/[^a-zA-Z0-9-]/g, "").slice(0, 36);
  return `c${consultorioId}-d${clean}@prontu.device`;
}

Deno.serve(async (request) => {
  if (request.method !== "POST") return response({ error: "Metodo nao permitido" }, 405);

  try {
    const body = await request.json();
    const chave = String(body.chave ?? "").trim();
    const deviceId = String(body.device_id ?? "").trim();
    const deviceName = String(body.device_name ?? "desktop").slice(0, 100);
    if (!chave || !deviceId) return response({ error: "Dados de ativacao invalidos" }, 400);

    const url = Deno.env.get("SUPABASE_URL") ?? "";
    const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    const anonKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
    if (!url || !serviceRole || !anonKey) return response({ error: "Servico indisponivel" }, 500);

    const admin = createClient(url, serviceRole, { auth: { persistSession: false } });
    const keyResult = await admin
      .from("chaves_acesso")
      .select("consultorio_id,nome_clinica")
      .eq("chave", chave)
      .maybeSingle();
    const row = keyResult.data;
    if (keyResult.error || !row?.consultorio_id) {
      return response({ error: "Chave invalida ou desativada" }, 401);
    }

    const consultorioId = Number(row.consultorio_id);
    const device = await admin
      .from("dispositivos_consultorio")
      .select("auth_user_id,revogado_em")
      .eq("consultorio_id", consultorioId)
      .eq("device_id", deviceId)
      .maybeSingle();
    if (device.data?.revogado_em) return response({ error: "Dispositivo desativado" }, 401);

    const email = deviceEmail(consultorioId, deviceId);
    const password = crypto.randomUUID() + crypto.randomUUID();
    const users = await admin.auth.admin.listUsers();
    const existing = users.data.users.find((user) => user.email === email);
    let userId: string;
    if (existing) {
      userId = existing.id;
      await admin.auth.admin.updateUserById(userId, { password });
    } else {
      const created = await admin.auth.admin.createUser({
        email, password, email_confirm: true,
        user_metadata: { consultorio_id: consultorioId, device_id: deviceId },
      });
      if (created.error || !created.data.user) return response({ error: "Ativacao indisponivel" }, 500);
      userId = created.data.user.id;
    }

    await admin.from("usuarios_consultorios").upsert(
      { auth_user_id: userId, consultorio_id: consultorioId },
      { onConflict: "auth_user_id,consultorio_id" },
    );
    await admin.from("dispositivos_consultorio").upsert(
      { consultorio_id: consultorioId, auth_user_id: userId, device_id: deviceId, device_name: deviceName, revogado_em: null },
      { onConflict: "consultorio_id,device_id" },
    );

    const auth = createClient(url, anonKey, { auth: { persistSession: false } });
    const signedIn = await auth.auth.signInWithPassword({ email, password });
    if (signedIn.error || !signedIn.data.session) return response({ error: "Ativacao indisponivel" }, 500);

    const session = signedIn.data.session;
    return response({
      access_token: session.access_token,
      refresh_token: session.refresh_token,
      expires_at: session.expires_at,
      consultorio_id: consultorioId,
      nome_clinica: row.nome_clinica,
      auth_user_id: userId,
    });
  } catch {
    return response({ error: "Ativacao indisponivel" }, 500);
  }
});

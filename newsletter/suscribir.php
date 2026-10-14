<?php
/**
 * suscribir.php — suscribe un email al newsletter en Doppler.
 *
 *  - Lista: LISTA_ID ("Suscriptores Web"). NUNCA la Base Maestra Activa (29291111).
 *  - Anti-spam igual que el sorteo: campo trampa (honeypot) + rechazo de envíos a
 *    menos de MIN_MS de haber aparecido el banner. El navegador manda cuánto tiempo
 *    pasó (campo "elapsed", medido con performance.now()), NO la hora de su reloj.
 *  - La cuenta y la API key de Doppler NO están acá ni en el repo: se leen de
 *    newsletter-config.php, que en producción vive FUERA de public_html (al lado de
 *    sorteo-data/). Ver newsletter-config.example.php.
 *  - Si Doppler falla (o falta la configuración) el email no se pierde: se guarda en
 *    newsletter-data/pendientes.csv (fuera de public_html; si no se puede, en
 *    newsletter/data/ protegida con .htaccess) y se avisa por mail a NOTIFICAR.
 *    Al visitante se le responde "ok": su suscripción quedó registrada.
 *  - Cada fallo tiene su propio code/msg para poder diagnosticarlo.
 *
 * Respuesta: JSON {ok:true, estado:"doppler"|"pendiente"} o {ok:false, code, msg}.
 *   code: method | nojs | fast | invalid | storage
 */
declare(strict_types=1);
ini_set('display_errors', '0');   // nunca mezclar avisos de PHP con la respuesta JSON
error_reporting(E_ALL);

const LISTA_ID = 29309044;        // "Suscriptores Web"
const BASE_MAESTRA = 29291111;    // "Base Maestra Activa": prohibido suscribir ahí desde la web
const NOTIFICAR = 'lucas@legendtravel.com.ar';
const REMITENTE = 'no-reply@legendtravel.com.ar';
const ORIGEN = 'Web legendtravel.com.ar';
const CONFIG_NOMBRE = 'newsletter-config.php';
const MIN_MS = 1500;              // tiempo mínimo entre ver el banner y enviar
const TIMEOUT_S = 8;              // espera máxima a Doppler antes de dejarlo pendiente

header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');

function responder(bool $ok, string $code = '', string $msg = '', array $extra = []): void {
    echo json_encode(array_merge(['ok' => $ok, 'code' => $code, 'msg' => $msg], $extra), JSON_UNESCAPED_UNICODE);
    exit;
}
function campo(string $k): string {
    $v = $_POST[$k] ?? '';
    return is_string($v) ? trim($v) : '';
}
/** La carpeta que contiene public_html (donde también viven sorteo-data/ y la configuración). */
function afuera_del_docroot(): ?string {
    $doc = rtrim((string) ($_SERVER['DOCUMENT_ROOT'] ?? ''), '/\\');
    return ($doc !== '' && dirname($doc) !== $doc) ? dirname($doc) : null;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    responder(false, 'method', 'Método no permitido.');
}

/* ---- anti-spam ---- */
if (campo('website') !== '') {            // campo trampa: un humano nunca lo completa
    responder(true, '', '', ['estado' => 'doppler']);   // se le responde "ok" para no dar pistas
}
$elapsed = campo('elapsed');
if ($elapsed === '' || !is_numeric($elapsed)) {
    responder(false, 'nojs', 'El formulario no terminó de cargar. Recargá la página y volvé a intentar.');
}
if ((float) $elapsed < MIN_MS) {
    responder(false, 'fast', 'Fue muy rápido: revisá el email y volvé a enviar.');
}

/* ---- validación ---- */
$email = strtolower(campo('email'));
if (!filter_var($email, FILTER_VALIDATE_EMAIL) || strlen($email) > 100) {
    responder(false, 'invalid', 'Revisá el email.');
}

/* ---- configuración (cuenta + API key), nunca dentro del repo ---- */
function config(): ?array {
    $cands = [];
    $afuera = afuera_del_docroot();
    if ($afuera !== null) $cands[] = $afuera . DIRECTORY_SEPARATOR . CONFIG_NOMBRE;   // producción
    $cands[] = __DIR__ . DIRECTORY_SEPARATOR . CONFIG_NOMBRE;                        // solo pruebas locales (está en .gitignore)
    foreach ($cands as $f) {
        if (!is_file($f) || !is_readable($f)) continue;
        $c = include $f;
        if (is_array($c) && trim((string) ($c['cuenta'] ?? '')) !== '' && trim((string) ($c['api_key'] ?? '')) !== '') return $c;
    }
    return null;
}

/* ---- Doppler: POST /accounts/{cuenta}/lists/{lista}/subscribers ---- */
function doppler(array $cfg, string $email): array {
    if (LISTA_ID === BASE_MAESTRA) return ['ok' => false, 'http' => 0, 'error' => '', 'detalle' => 'LISTA_ID apunta a la Base Maestra: bloqueado'];
    if (!function_exists('curl_init')) return ['ok' => false, 'http' => 0, 'error' => '', 'detalle' => 'PHP sin extensión curl'];
    $url = 'https://restapi.fromdoppler.com/accounts/' . rawurlencode(trim((string) $cfg['cuenta']))
         . '/lists/' . LISTA_ID . '/subscribers';
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode(['email' => $email]),
        CURLOPT_HTTPHEADER => [
            'Authorization: token ' . trim((string) $cfg['api_key']),
            'Content-Type: application/json',
            'Accept: application/json',
            'X-Doppler-Subscriber-Origin: ' . ORIGEN,
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => TIMEOUT_S,
    ]);
    $body = curl_exec($ch);
    $http = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);
    if ($body === false) return ['ok' => false, 'http' => 0, 'error' => '', 'detalle' => 'curl: ' . $err];
    $j = json_decode((string) $body, true);
    return [
        'ok' => $http >= 200 && $http < 300,
        'http' => $http,
        'error' => is_array($j) ? (string) ($j['errorCode'] ?? '') : '',   // p. ej. "4" = 400.4 invalid-email
        'detalle' => substr(preg_replace('/\s+/', ' ', (string) $body), 0, 400),
    ];
}

/* ---- carpeta de datos (nunca pública), igual que el sorteo ---- */
function carpeta_datos(): ?string {
    $cands = [];
    $afuera = afuera_del_docroot();
    if ($afuera !== null) $cands[] = $afuera . DIRECTORY_SEPARATOR . 'newsletter-data';
    $cands[] = __DIR__ . DIRECTORY_SEPARATOR . 'data';
    foreach ($cands as $dir) {
        if (!is_dir($dir)) @mkdir($dir, 0750, true);
        if (!is_dir($dir) || !is_writable($dir)) continue;
        // aunque la carpeta quede dentro del docroot, Apache no la sirve
        if (!file_exists($dir . '/.htaccess')) @file_put_contents($dir . '/.htaccess', "Require all denied\nDeny from all\n");
        if (!file_exists($dir . '/index.html')) @file_put_contents($dir . '/index.html', '');
        return $dir;
    }
    return null;
}

$fecha = date('Y-m-d H:i:s');
$dir = carpeta_datos();
$log = $dir !== null ? $dir . DIRECTORY_SEPARATOR . 'newsletter.log' : null;
function anotar(?string $log, string $linea): void {
    if ($log !== null) @file_put_contents($log, $linea . "\n", FILE_APPEND | LOCK_EX);
}

$cfg = config();
$r = $cfg !== null ? doppler($cfg, $email)
                   : ['ok' => false, 'http' => 0, 'error' => '', 'detalle' => 'falta ' . CONFIG_NOMBRE . ' (cuenta y api_key)'];

if ($r['ok']) {
    anotar($log, "$fecha\t$email\tdoppler\thttp={$r['http']}");
    responder(true, '', '', ['estado' => 'doppler']);
}
if ($r['http'] === 400 && $r['error'] === '4') {          // Doppler dice que el email no es válido
    anotar($log, "$fecha\t$email\tinvalid\t{$r['detalle']}");
    responder(false, 'invalid', 'Revisá el email.');
}

/* ---- Doppler falló: el email queda en pendientes.csv y se avisa por mail ---- */
$motivo = $r['http'] > 0 ? "HTTP {$r['http']}: {$r['detalle']}" : $r['detalle'];
$guardado = false;
$csv = $dir !== null ? $dir . DIRECTORY_SEPARATOR . 'pendientes.csv' : null;
if ($csv !== null && ($fh = @fopen($csv, 'c+')) !== false) {
    flock($fh, LOCK_EX);
    $nuevo = fstat($fh)['size'] === 0;
    fseek($fh, 0, SEEK_END);
    if ($nuevo) fputcsv($fh, ['fecha', 'email', 'lista', 'motivo']);
    $guardado = fputcsv($fh, [$fecha, $email, (string) LISTA_ID, $motivo]) !== false;
    fflush($fh);
    flock($fh, LOCK_UN);
    fclose($fh);
}

$asunto = 'Newsletter — Doppler falló, suscripción pendiente: ' . $email;
$cuerpo = "No se pudo suscribir un email a la lista " . LISTA_ID . " (Suscriptores Web) de Doppler.\n\n"
    . "Fecha: $fecha\nEmail: $email\nMotivo: $motivo\n\n"
    . ($guardado ? "Quedó guardado en: $csv\nCargalo a mano en Doppler (o reimportá el CSV) y borrá la fila.\n"
                 : "ATENCIÓN: tampoco se pudo guardar en pendientes.csv. Este mail es el único registro.\n");
$cabeceras = 'From: Legend Travel <' . REMITENTE . ">\r\nContent-Type: text/plain; charset=UTF-8\r\n";
$enviado = false;
try {
    $enviado = @mail(NOTIFICAR, '=?UTF-8?B?' . base64_encode($asunto) . '?=', $cuerpo, $cabeceras);
} catch (Throwable $e) { $enviado = false; }
anotar($log, "$fecha\t$email\tpendiente\tcsv=" . ($guardado ? 'ok' : 'FALLO') . "\tmail=" . ($enviado ? 'ok' : 'FALLO') . "\t$motivo");

if (!$guardado && !$enviado) {
    http_response_code(500);
    responder(false, 'storage', 'No pudimos registrar tu email. Probá de nuevo en un rato o escribinos por WhatsApp.');
}
responder(true, '', '', ['estado' => 'pendiente']);   // el email quedó registrado aunque Doppler haya fallado

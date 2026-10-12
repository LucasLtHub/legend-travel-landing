<?php
/**
 * contacto/enviar.php — recibe el formulario de consulta de /contacto/.
 *
 *  - Valida del lado del servidor; campo trampa (honeypot) y tiempo mínimo
 *    medido por el navegador con performance.now() (campo "elapsed"), nunca
 *    la hora del reloj del equipo.
 *  - Guarda cada consulta en un CSV FUERA de public_html (../contacto-data/,
 *    al lado de ../sorteo-data/); si no puede, en contacto/data/ protegida con
 *    .htaccess "Deny from all". No deduplica: cada consulta es una fila.
 *  - Avisa por mail a NOTIFICAR con copia a COPIA; si mail() falla no bloquea:
 *    el CSV es la fuente de verdad y el fallo queda en el log.
 *  - Cada fallo tiene su propio code/msg para poder diagnosticarlo.
 *
 * Respuesta: JSON {ok:true, mail:"ok"|"fallo"} o {ok:false, code, msg[, campos]}.
 *   code: method | nojs | fast | invalid | storage_dir | storage_open | storage_write
 */
declare(strict_types=1);
ini_set('display_errors', '0');
error_reporting(E_ALL);
date_default_timezone_set('America/Argentina/Buenos_Aires');

const NOTIFICAR = 'promociones@legendtravel.com.ar';
const COPIA = 'lucas@legendtravel.com.ar';
const REMITENTE = 'no-reply@legendtravel.com.ar';
const CSV_NOMBRE = 'consultas-web.csv';
const MIN_MS = 1500;

header('Content-Type: application/json; charset=utf-8');
header('X-Robots-Tag: noindex, nofollow');
header('Cache-Control: no-store');

function responder(bool $ok, string $code = '', string $msg = '', array $extra = []): void {
    echo json_encode(array_merge(['ok' => $ok, 'code' => $code, 'msg' => $msg], $extra), JSON_UNESCAPED_UNICODE);
    exit;
}
function campo(string $k): string {
    $v = $_POST[$k] ?? '';
    return is_string($v) ? trim(str_replace(["\r", "\0"], '', $v)) : '';
}
function largo(string $s): int { return function_exists('mb_strlen') ? mb_strlen($s, 'UTF-8') : strlen($s); }

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    responder(false, 'method', 'Método no permitido.');
}

/* ---- anti-spam ---- */
if (campo('website') !== '') responder(true, '', '', ['mail' => 'ok']);   // campo trampa: se responde "ok" para no dar pistas
$elapsed = campo('elapsed');
if ($elapsed === '' || !is_numeric($elapsed)) responder(false, 'nojs', 'El formulario no terminó de cargar. Recargá la página y volvé a intentar.');
if ((float) $elapsed < MIN_MS) responder(false, 'fast', 'Fue muy rápido: revisá los datos y volvé a enviar.');

/* ---- validación ---- */
$d = [
    'nombre' => campo('nombre'), 'email' => strtolower(campo('email')), 'celular' => campo('celular'),
    'pasajeros' => campo('pasajeros'), 'menores' => campo('menores'), 'fechas' => campo('fechas'),
    'destino' => campo('destino'), 'noches' => campo('noches'), 'presupuesto' => campo('presupuesto'),
    'detalles' => campo('detalles'),
];
$errores = [];
if (largo($d['nombre']) < 2 || largo($d['nombre']) > 120) $errores['nombre'] = 'Ingresá tu nombre y apellido.';
if (!filter_var($d['email'], FILTER_VALIDATE_EMAIL) || strlen($d['email']) > 120) $errores['email'] = 'Revisá el email.';
$dig = preg_replace('/\D+/', '', $d['celular']);
if (strlen($dig) < 8 || strlen($dig) > 20) $errores['celular'] = 'Ingresá tu celular con código de área.';
if (!preg_match('/^\d{1,3}$/', $d['pasajeros']) || (int) $d['pasajeros'] < 1) $errores['pasajeros'] = 'Indicá cuántos pasajeros viajan.';
if (largo($d['fechas']) < 3 || largo($d['fechas']) > 200) $errores['fechas'] = 'Contanos las fechas posibles.';
if (largo($d['destino']) < 2 || largo($d['destino']) > 200) $errores['destino'] = 'Contanos el destino.';
if ($d['noches'] !== '' && !preg_match('/^\d{1,3}$/', $d['noches'])) $errores['noches'] = 'Indicá un número de noches.';
foreach (['menores' => 200, 'presupuesto' => 200, 'detalles' => 2000] as $k => $max) {
    if (largo($d[$k]) > $max) $errores[$k] = 'El texto es demasiado largo.';
}
if ($errores) {
    echo json_encode(['ok' => false, 'code' => 'invalid', 'msg' => 'Revisá los datos marcados.', 'campos' => $errores], JSON_UNESCAPED_UNICODE);
    exit;
}

/* ---- carpeta de datos (nunca pública) ---- */
function carpeta_datos(): ?string {
    $cands = [];
    $doc = rtrim((string) ($_SERVER['DOCUMENT_ROOT'] ?? ''), '/\\');
    if ($doc !== '' && dirname($doc) !== $doc) $cands[] = dirname($doc) . DIRECTORY_SEPARATOR . 'contacto-data';
    $cands[] = __DIR__ . DIRECTORY_SEPARATOR . 'data';
    foreach ($cands as $dir) {
        if (!is_dir($dir)) @mkdir($dir, 0750, true);
        if (!is_dir($dir) || !is_writable($dir)) continue;
        if (!file_exists($dir . '/.htaccess')) @file_put_contents($dir . '/.htaccess', "Require all denied\nDeny from all\n");
        if (!file_exists($dir . '/index.html')) @file_put_contents($dir . '/index.html', '');
        return $dir;
    }
    return null;
}
$dir = carpeta_datos();
if ($dir === null) {
    http_response_code(500);
    responder(false, 'storage_dir', 'No pudimos registrar tu consulta (carpeta de datos sin permisos). Escribinos por WhatsApp y te respondemos.');
}
$csv = $dir . DIRECTORY_SEPARATOR . CSV_NOMBRE;
$log = $dir . DIRECTORY_SEPARATOR . 'consultas-web.log';

$fh = @fopen($csv, 'a');
if ($fh === false) {
    http_response_code(500);
    responder(false, 'storage_open', 'No pudimos registrar tu consulta (no se pudo abrir el archivo). Escribinos por WhatsApp y te respondemos.');
}
flock($fh, LOCK_EX);
$nuevo = fstat($fh)['size'] === 0;
if ($nuevo) fputcsv($fh, ['fecha', 'nombre', 'email', 'celular', 'pasajeros', 'menores', 'fechas', 'destino', 'noches', 'presupuesto', 'detalles']);
$fecha = date('Y-m-d H:i:s');
$escrito = fputcsv($fh, array_merge([$fecha], array_values($d)));
fflush($fh);
flock($fh, LOCK_UN);
fclose($fh);
if ($escrito === false) {
    http_response_code(500);
    responder(false, 'storage_write', 'No pudimos registrar tu consulta (fallo al escribir). Escribinos por WhatsApp y te respondemos.');
}

/* ---- aviso por mail (no bloquea) ---- */
$asunto = 'Nueva consulta web: ' . $d['destino'] . ' — ' . $d['nombre'];
$cuerpo = "Nueva consulta desde el formulario web\n\n"
    . "Fecha (hora argentina): $fecha\n"
    . "Nombre y apellido: {$d['nombre']}\nEmail: {$d['email']}\nCelular: {$d['celular']}\n"
    . "Cantidad de pasajeros: {$d['pasajeros']}\nMenores (edades): " . ($d['menores'] ?: '-') . "\n"
    . "Fechas posibles: {$d['fechas']}\nDestino: {$d['destino']}\n"
    . "Cantidad de noches: " . ($d['noches'] ?: '-') . "\nPresupuesto orientativo: " . ($d['presupuesto'] ?: '-') . "\n"
    . "Otros detalles: " . ($d['detalles'] ?: '-') . "\n";
$cabeceras = 'From: Legend Travel <' . REMITENTE . ">\r\nCc: " . COPIA . "\r\nReply-To: {$d['email']}\r\nContent-Type: text/plain; charset=UTF-8\r\n";
$enviado = false;
try {
    $enviado = @mail(NOTIFICAR, '=?UTF-8?B?' . base64_encode($asunto) . '?=', $cuerpo, $cabeceras);
} catch (Throwable $e) { $enviado = false; }
@file_put_contents($log, "$fecha\t{$d['email']}\tmail=" . ($enviado ? 'ok' : 'FALLO') . "\n", FILE_APPEND);

responder(true, '', '', ['mail' => $enviado ? 'ok' : 'fallo']);
